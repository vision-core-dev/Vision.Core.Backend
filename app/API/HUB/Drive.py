import uuid
import json
import tempfile
import os
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from sqlalchemy import select, delete, or_, and_, literal_column, text, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb, async_session
from app.Infrastructure.Storage import _upload_to_bunny, _upload_stream_to_bunny, _delete_from_bunny, UPLOAD_PROGRESS
from app.Objects.DriveModel import (
    DriveFolder, DriveFile, DriveAccessType,
    DriveFolderPreview, DriveFilePreview, DriveListResponse,
    TaskDiskFile
)
from app.Objects.UserModel import User
from app.Objects.tasks.TaskAttachment import TaskAttachment
from app.Objects.tasks.TaskModel import Task
from app.Objects.tasks.BoardModel import Board
from app.Services.Hub.AuthService.depends import getuser

drive_router = APIRouter(prefix="/Drive", tags=["Drive"])


def _can_access(item, user: User) -> bool:
    """Check if user can access a drive item (folder or file). Used for single-item checks."""
    if str(item.owner_id) == str(user.id):
        return True
    if user.role and user.role.order <= 1:
        return True

    access = item.access_type
    if isinstance(access, DriveAccessType):
        access = access.value

    if access == "public":
        return True
    if access == "private":
        return False
    if access == "role":
        allowed = item.allowed_role_ids or []
        return user.role_id in allowed
    return False


def _access_filter(model, user: User):
    """Build a SQL WHERE clause for access control — avoids loading all rows into Python."""
    if user.role and user.role.order <= 1:
        return True  # admins see everything; SQLAlchemy treats True as no filter

    conditions = [
        model.owner_id == user.id,
        model.access_type == DriveAccessType.public,
    ]
    if user.role_id:
        conditions.append(
            and_(
                model.access_type == DriveAccessType.role,
                model.allowed_role_ids.any(user.role_id),
            )
        )
    return or_(*conditions)


@drive_router.get("/List")
async def list_drive(
    folder_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """List folders and files in a directory with pagination."""
    parsed_folder_id = uuid.UUID(folder_id) if folder_id and folder_id != "null" else None

    if parsed_folder_id:
        folder = await db.get(DriveFolder, parsed_folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="folder_not_found")
        if not _can_access(folder, user):
            raise HTTPException(status_code=403, detail="access_denied")

    # Fetch folders (access-filtered in SQL)
    access = _access_filter(DriveFolder, user)
    q_folders = select(DriveFolder).where(
        DriveFolder.parent_id == parsed_folder_id,
    ).order_by(DriveFolder.name)
    if access is not True:
        q_folders = q_folders.where(access)
    res_folders = await db.execute(q_folders)
    folders = res_folders.scalars().all()

    # Fetch files (access-filtered in SQL, with pagination)
    access_f = _access_filter(DriveFile, user)
    q_files = select(DriveFile).where(
        DriveFile.folder_id == parsed_folder_id,
        DriveFile.task_attachment_id == None,
    ).order_by(DriveFile.name).limit(limit).offset(offset)
    if access_f is not True:
        q_files = q_files.where(access_f)
    res_files = await db.execute(q_files)
    files = res_files.scalars().all()

    # Breadcrumbs via recursive CTE (single query instead of N+1)
    breadcrumbs = []
    current_folder = None
    if parsed_folder_id:
        cte = (
            select(DriveFolder)
            .where(DriveFolder.id == parsed_folder_id)
            .cte(name="breadcrumb_cte", recursive=True)
        )
        cte = cte.union_all(
            select(DriveFolder).join(cte, DriveFolder.id == cte.c.parent_id)
        )
        bc_query = select(DriveFolder).join(cte, DriveFolder.id == cte.c.id).order_by(DriveFolder.created_at)
        bc_result = await db.execute(bc_query)
        breadcrumbs = list(bc_result.scalars().all())
        # current_folder is the last breadcrumb (the folder we're viewing)
        current_folder = breadcrumbs[-1] if breadcrumbs else None

    return {
        "folders": [DriveFolderPreview.from_orm(f) for f in folders],
        "files": [DriveFilePreview.from_orm(f) for f in files],
        "current_folder": DriveFolderPreview.from_orm(current_folder) if current_folder else None,
        "breadcrumbs": [DriveFolderPreview.from_orm(f) for f in breadcrumbs],
    }


@drive_router.post("/Folders/Create")
async def create_folder(
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Create a new folder."""
    parent_id = uuid.UUID(data["parent_id"]) if data.get("parent_id") else None

    folder = DriveFolder(
        name=data["name"],
        parent_id=parent_id,
        owner_id=user.id,
        access_type=data.get("access_type", DriveAccessType.public),
        allowed_role_ids=[uuid.UUID(r) for r in data.get("allowed_role_ids", [])],
    )
    db.add(folder)
    await db.commit()
    return DriveFolderPreview.from_orm(folder)


@drive_router.patch("/Folders/{folder_id}")
async def update_folder(
    folder_id: str,
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Update folder details."""
    folder = await db.get(DriveFolder, uuid.UUID(folder_id))
    if not folder:
        raise HTTPException(status_code=404, detail="folder_not_found")
    if str(folder.owner_id) != str(user.id) and (not user.role or user.role.order > 1):
        raise HTTPException(status_code=403, detail="access_denied")

    if "name" in data: folder.name = data["name"]
    if "access_type" in data: folder.access_type = data["access_type"]
    if "allowed_role_ids" in data: folder.allowed_role_ids = [uuid.UUID(r) for r in data["allowed_role_ids"]]
    
    if "parent_id" in data:
        p_id = data["parent_id"]
        folder.parent_id = uuid.UUID(p_id) if p_id and str(p_id).lower() != "null" else None

    await db.commit()
    return DriveFolderPreview.from_orm(folder)


@drive_router.delete("/Folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Delete a folder and its contents."""
    folder = await db.get(DriveFolder, uuid.UUID(folder_id))
    if not folder:
        raise HTTPException(status_code=404, detail="folder_not_found")
    if str(folder.owner_id) != str(user.id) and (not user.role or user.role.order > 1):
        raise HTTPException(status_code=403, detail="access_denied")

    await db.delete(folder)
    await db.commit()
    return {"ok": True}


import tempfile
import shutil
import os

async def process_file_upload(
    temp_path: str,
    file_name: str,
    content_type: str,
    file_size: int,
    parsed_folder_id: Optional[uuid.UUID],
    owner_id: uuid.UUID,
    access_type: DriveAccessType,
    parsed_role_ids: list[uuid.UUID],
    upload_id: str,
):
    try:
        ext = file_name.split(".")[-1] if "." in file_name else ""
        unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
        storage_path = f"drive/{owner_id}/{unique_name}"

        file_url = await _upload_stream_to_bunny(storage_path, temp_path, content_type or "application/octet-stream", upload_id)

        async with async_session() as db:
            drive_file = DriveFile(
                folder_id=parsed_folder_id,
                owner_id=owner_id,
                name=file_name,
                url=file_url,
                size=file_size,
                mime_type=content_type,
                access_type=access_type,
                allowed_role_ids=parsed_role_ids,
            )
            db.add(drive_file)
            await db.commit()
    except Exception as e:
        print(f"Background upload failed: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@drive_router.post("/Files/Upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    access_type: DriveAccessType = Form(DriveAccessType.public),
    allowed_role_ids: Optional[str] = Form(None),
    upload_id: Optional[str] = Query(None),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Upload a file inside a background task to prevent cloudflare 100s timeout."""
    parsed_folder_id = uuid.UUID(folder_id) if folder_id and folder_id != "null" and folder_id != "" else None

    if parsed_folder_id:
        folder = await db.get(DriveFolder, parsed_folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="folder_not_found")
        if not _can_access(folder, user):
            raise HTTPException(status_code=403, detail="access_denied")

    # Use a real temp file on disk so we don't block the memory/db
    fd, temp_path = tempfile.mkstemp()
    
    await file.seek(0)
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(temp_path)

    parsed_role_ids = []
    if allowed_role_ids:
        parsed_role_ids = [uuid.UUID(r.strip()) for r in allowed_role_ids.split(",") if r.strip()]

    background_tasks.add_task(
        process_file_upload,
        temp_path,
        file.filename,
        file.content_type,
        file_size,
        parsed_folder_id,
        user.id,
        access_type,
        parsed_role_ids,
        upload_id,
    )

    return {"status": "processing", "upload_id": upload_id}


@drive_router.websocket("/Files/UploadWS")
async def upload_file_ws(websocket: WebSocket, db: AsyncSession = Depends(getdb)):
    """WebSocket endpoint for large file uploads to bypass cloudflare timeouts."""
    from app.Services.Hub.AuthService.depends import _get_user_by_token
    await websocket.accept()
    
    try:
        # 1. First message must be JSON config with token
        auth_msg_raw = await websocket.receive_text()
        auth_msg = json.loads(auth_msg_raw)
        
        token_str = auth_msg.get("token")
        if not token_str:
            await websocket.close(code=1008)
            return
            
        try:
            user = await _get_user_by_token(db, uuid.UUID(token_str))
        except Exception:
            await websocket.close(code=1008)
            return
            
        folder_id = auth_msg.get("folder_id")
        parsed_folder_id = uuid.UUID(folder_id) if folder_id and folder_id != "null" and folder_id != "" else None

        if parsed_folder_id:
            folder = await db.get(DriveFolder, parsed_folder_id)
            if not folder or not _can_access(folder, user):
                await websocket.close(code=1008)
                return

        # Tell client we are ready
        await websocket.send_json({"status": "ready"})
        
        # 2. Receive binary chunks into a temporary file
        fd, temp_path = tempfile.mkstemp()
        
        with os.fdopen(fd, "wb") as f:
            while True:
                msg = await websocket.receive()
                if "bytes" in msg:
                    await asyncio.to_thread(f.write, msg["bytes"])
                elif "text" in msg:
                    data = json.loads(msg["text"])
                    if data.get("type") == "eof":
                        break
        
        # 3. File is fully received, spawn background processing task
        parsed_role_ids = []
        if auth_msg.get("allowed_role_ids"):
            parsed_role_ids = [uuid.UUID(r) for r in auth_msg.get("allowed_role_ids")]
            
        asyncio.create_task(
            process_file_upload(
                temp_path,
                auth_msg.get("filename", "unnamed_file"),
                auth_msg.get("content_type", "application/octet-stream"),
                os.path.getsize(temp_path),
                parsed_folder_id,
                user.id,
                DriveAccessType(auth_msg.get("access_type", "public")),
                parsed_role_ids,
                auth_msg.get("upload_id")
            )
        )
        await websocket.send_json({"status": "success", "message": "File received. Processing."})
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("WS Upload Error: ", e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@drive_router.get("/Files/UploadStatus/{upload_id}")
async def get_upload_status(upload_id: str):
    """Get the progress of an ongoing upload stream (Server -> Bunny)."""
    progress = UPLOAD_PROGRESS.get(upload_id)
    if progress is None:
        return {"progress": 100, "status": "completed_or_not_found"}
    return {"progress": progress, "status": "streaming"}


@drive_router.patch("/Files/{file_id}")
async def update_file(
    file_id: str,
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Update file details."""
    d_file = await db.get(DriveFile, uuid.UUID(file_id))
    if not d_file:
        raise HTTPException(status_code=404, detail="file_not_found")
    if str(d_file.owner_id) != str(user.id) and (not user.role or user.role.order > 1):
        raise HTTPException(status_code=403, detail="access_denied")

    if "name" in data: d_file.name = data["name"]
    if "access_type" in data: d_file.access_type = data["access_type"]
    if "allowed_role_ids" in data: d_file.allowed_role_ids = [uuid.UUID(r) for r in data["allowed_role_ids"]]

    if "folder_id" in data:
        f_id = data["folder_id"]
        d_file.folder_id = uuid.UUID(f_id) if f_id and str(f_id).lower() != "null" else None

    await db.commit()
    return DriveFilePreview.from_orm(d_file)


@drive_router.delete("/Files/{file_id}")
async def delete_file(
    file_id: str,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Delete a file."""
    d_file = await db.get(DriveFile, uuid.UUID(file_id))
    if not d_file:
        raise HTTPException(status_code=404, detail="file_not_found")
    if str(d_file.owner_id) != str(user.id) and (not user.role or user.role.order > 1):
        raise HTTPException(status_code=403, detail="access_denied")

    # Optionally delete from Bunny too
    # await _delete_from_bunny(d_file.url.split(".com/")[-1])

    await db.delete(d_file)
    await db.commit()
    return {"ok": True}


@drive_router.get("/TaskDisk")
async def task_disk(
    board_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Virtual view of task attachments with pagination."""
    from sqlalchemy.orm import selectinload
    q = select(TaskAttachment).options(
        selectinload(TaskAttachment.task).selectinload(Task.board)
    )
    if board_id:
        q = q.join(Task).join(Board).where(Board.id == uuid.UUID(board_id))

    q = q.order_by(TaskAttachment.created_at.desc()).limit(limit).offset(offset)

    res = await db.execute(q)
    attachments = res.scalars().all()

    return {
        "files": [
            {
                "id": str(a.id),
                "name": a.name or a.url.split("/")[-1],
                "url": a.url,
                "task_id": str(a.task_id) if a.task_id else None,
                "task_name": a.task.name if a.task else "Unknown",
                "board_id": str(a.task.board_id) if a.task and a.task.board_id else None,
                "board_name": a.task.board.name if a.task and a.task.board else "Unknown",
                "created_at": a.created_at,
            }
            for a in attachments
        ]
    }


@drive_router.get("/Search")
async def search_drive(
    q: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Search for files and folders with pagination and SQL-level access check."""
    # Escape special SQL LIKE characters to prevent injection
    safe_q = q.replace("%", "\\%").replace("_", "\\_")

    # Folders
    q_folders = select(DriveFolder).where(DriveFolder.name.ilike(f"%{safe_q}%"))
    access_fold = _access_filter(DriveFolder, user)
    if access_fold is not True:
        q_folders = q_folders.where(access_fold)
    q_folders = q_folders.order_by(DriveFolder.name).limit(limit).offset(offset)

    # Files
    q_files = select(DriveFile).where(DriveFile.name.ilike(f"%{safe_q}%"))
    access_file = _access_filter(DriveFile, user)
    if access_file is not True:
        q_files = q_files.where(access_file)
    q_files = q_files.order_by(DriveFile.name).limit(limit).offset(offset)

    res_folders = await db.execute(q_folders)
    res_files = await db.execute(q_files)

    folders = res_folders.scalars().all()
    files = res_files.scalars().all()

    return {
        "folders": [DriveFolderPreview.from_orm(f) for f in folders],
        "files": [DriveFilePreview.from_orm(f) for f in files],
    }
