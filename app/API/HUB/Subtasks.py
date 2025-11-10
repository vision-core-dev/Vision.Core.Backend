import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.TaskService import TaskService

subtasks_router = APIRouter(prefix="/{task_id}/Subtasks", tags=["Subtasks"])


@subtasks_router.get("/Get")
async def get_all_subtasks(
    task_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await TaskService(db).GetSubtasks(task_id, user)

@subtasks_router.post("/Create")
async def create_subtask(
    task_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name_required")
    return await TaskService(db).CreateSubtask(task_id, name, user)

@subtasks_router.post("/{subtask_id}/SetCompleted")
async def set_subtask_completed(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    is_completed = payload.get("is_completed")
    if is_completed is None:
        raise HTTPException(status_code=400, detail="is_completed_required")
    return await TaskService(db).SetSubtaskCompleted(task_id, subtask_id, is_completed, user)

@subtasks_router.post("/{subtask_id}/Rename")
async def rename_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    new_name = payload.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="new_name_required")
    return await TaskService(db).RenameSubtask(task_id, subtask_id, new_name, user)

@subtasks_router.post("/{subtask_id}/Delete")
async def delete_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await TaskService(db).DeleteSubtask(task_id, subtask_id, user)