import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser
from app.Objects.UserModel import User
from app.Services.Hub.TaskService import TaskService
from app.Services.Hub.TaskService.contracts import TaskDetailsResponse

tasks_router = APIRouter(prefix="/Tasks", tags=["Tasks"])

# 🔹 Деталі задачі
@tasks_router.get("/{task_id}/GetDetails", response_model=TaskDetailsResponse)
async def get_task_details(task_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await TaskService(db).GetTaskDetails(task_id, user)

# 🔹 Призначити користувача
@tasks_router.post("/{task_id}/AssignUser")
async def assign_user(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id_required")
    return await TaskService(db).AssignUser(task_id, uuid.UUID(user_id))

# 🔹 Зняти користувача
@tasks_router.post("/{task_id}/UnassignUser")
async def unassign_user(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id_required")
    return await TaskService(db).UnassignUser(task_id, uuid.UUID(user_id))

# 🔹 Додати мітку
@tasks_router.post("/{task_id}/AssignTag")
async def assign_tag(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    tag_id = payload.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id_required")
    return await TaskService(db).AssignTag(task_id, uuid.UUID(tag_id))

# 🔹 Зняти мітку
@tasks_router.post("/{task_id}/UnassignTag")
async def unassign_tag(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    tag_id = payload.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id_required")
    return await TaskService(db).UnassignTag(task_id, uuid.UUID(tag_id))

# 🔹 Архівувати задачу
@tasks_router.post("/{task_id}/Archive")
async def archive_task(task_id: uuid.UUID, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    return await TaskService(db).ArchiveTask(task_id, user)


@tasks_router.post("/{task_id}/UpdateDescription")
async def update_task_description(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    description = payload.get("description")
    if description is None:
        raise HTTPException(status_code=400, detail="description_required")
    return await TaskService(db).UpdateTaskDescription(task_id, description, user)


@tasks_router.post("/{task_id}/UpdateName")
async def update_task_name(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    name = payload.get("name")
    if name is None:
        raise HTTPException(status_code=400, detail="name_required")
    return await TaskService(db).UpdateTaskName(task_id, name, user)


@tasks_router.post("/{task_id}/Attachments/UploadFile")
async def upload_task_attachment(task_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    return await TaskService(db).UploadFileAttachment(task_id, file, user)

@tasks_router.post("/{task_id}/Attachments/RemoveFile")
async def remove_task_attachment(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    attachment_id = payload.get("attachment_id")
    if not attachment_id:
        raise HTTPException(status_code=400, detail="attachment_id_required")
    return await TaskService(db).RemoveFileAttachment(task_id, uuid.UUID(attachment_id), user)

@tasks_router.post("/{task_id}/Attachments/{attachment_id}/Rename")
async def rename_task_attachment(task_id: uuid.UUID, attachment_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    new_name = payload.get("new_name")
    if new_name is None:
        raise HTTPException(status_code=400, detail="new_name_required")
    return await TaskService(db).RenameAttachment(task_id, attachment_id, new_name, user)


@tasks_router.post("/{task_id}/UploadBanner")
async def upload_task_banner(
    task_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await TaskService(db).UploadTaskBanner(task_id, file, user)