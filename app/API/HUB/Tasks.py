import uuid
from fastapi import APIRouter, Depends, HTTPException
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
