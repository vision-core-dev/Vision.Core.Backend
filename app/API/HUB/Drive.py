import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy import select, delete, or_
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
    """Check if user can access a drive item (folder or file)."""
    # Owner always has access
    if str(item.owner_id) == str(user.id):
        return True

    # Admins (order <= 1) always have access
    if user.role and user.role.order <= 1:
        return True

    access = item.access_type
    if isinstance(access, DriveAccessType):
        access = access.value

    if access == "public":
        return True
    if access == "private":
        return False  # Already checked owner above
    if access == "role":
        allowed = item.allowed_role_ids or []
        return user.role_id in allowed
    return False


@drive_router.get("/List")
async def list_drive(
    folder_id: Optional[str] = None,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """List folders and files in a directory."""
    parsed_folder_id = uuid.UUID(folder_id) if folder_id and folder_id != "null" else None

    if parsed_folder_id:
        folder = await db.get(DriveFolder, parsed_folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="folder_not_found")
        if not _can_access(folder, user):
            raise HTTPException(status_code=403, detail="access_denied")

    # Fetch folders
    q_folders = select(DriveFolder).where(DriveFolder.parent_id == parsed_folder_id).order_by(DriveFolder.name)
    res_folders = await db.execute(q_folders)
    folders = [f for f in res_folders.scalars().all() if _can_access(f, user)]

    # Fetch files
    q_files = select(DriveFile).where(
        DriveFile.folder_id == parsed_folder_id,
        DriveFile.task_attachment_id == None,
    ).order_by(DriveFile.name)
    res_files = await db.execute(q_files)
    files = [f for f in res_files.scalars().all() if _can_access(f, user)]

    # Breadcrumbs
    breadcrumbs = []
    if parsed_folder_id:
        curr = await db.get(DriveFolder, parsed_folder_id)
        while curr:
            breadcrumbs.insert(0, curr)
            if curr.parent_id:
                curr = await db.get(DriveFolder, curr.parent_id)
            else:
                curr = None

    return {
        "folders": [DriveFolderPreview.from_orm(f) for f in folders],
        "files": [DriveFilePreview.from_orm(f) for f in files],
        "current_folder": DriveFolderPreview.from_orm(await db.get(DriveFolder, parsed_folder_id)) if parsed_folder_id else None,
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
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Virtual view of task attachments."""
    from sqlalchemy.orm import selectinload
    q = select(TaskAttachment).options(
        selectinload(TaskAttachment.task).selectinload(Task.board)
    )
    if board_id:
        q = q.join(Task).join(Board).where(Board.id == uuid.UUID(board_id))

    res = await db.execute(q)
    attachments = res.scalars().all()

    return {
        "files": [
            {
                "id": str(a.id),
                "name": a.name or a.url.split("/")[-1],
                "url": a.url,
                "created_at": a.created_at,
                "board_name": a.task.board.name if a.task and a.task.board else "Unknown"
            }
            for a in attachments
        ]
    }


@drive_router.get("/Search")
async def search_drive(
    q: str,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """Search for files and folders."""
    q_folders = select(DriveFolder).where(DriveFolder.name.ilike(f"%{q}%"))
    q_files = select(DriveFile).where(DriveFile.name.ilike(f"%{q}%"))

    res_folders = await db.execute(q_folders)
    res_files = await db.execute(q_files)

    folders = [f for f in res_folders.scalars().all() if _can_access(f, user)]
    files = [f for f in res_files.scalars().all() if _can_access(f, user)]

    return {
        "folders": [DriveFolderPreview.from_orm(f) for f in folders],
        "files": [DriveFilePreview.from_orm(f) for f in files],
    }
