import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.TaskService import TaskService
from app.Objects.tasks.TaskModel import Task

async def _notify_update(board_id, action, data):
    try:
        from app.API.HUB.Boards.websocket import notify_board_update
        await notify_board_update(board_id, action, data)
    except Exception as e:
        print(f"Error notifying WS: {e}")

subtasks_router = APIRouter(prefix="/{task_id}/Subtasks", tags=["Subtasks"])


@subtasks_router.get("/Get")
async def get_all_subtasks(
    task_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    await TaskService(db).CheckTaskAccess(task_id, user)
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
    await TaskService(db).CheckTaskAccess(task_id, user)
    res = await TaskService(db).CreateSubtask(task_id, name, user)
    # Notify board
    task = await db.get(Task, task_id)
    if task:
        await _notify_update(str(task.board_id), "task_updated", {"task_id": str(task_id)})
    return res

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
    await TaskService(db).CheckTaskAccess(task_id, user)
    res = await TaskService(db).SetSubtaskCompleted(task_id, subtask_id, is_completed, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

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
    await TaskService(db).CheckTaskAccess(task_id, user)
    res = await TaskService(db).RenameSubtask(task_id, subtask_id, new_name, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

@subtasks_router.post("/{subtask_id}/Delete")
async def delete_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    await TaskService(db).CheckTaskAccess(task_id, user)
    res = await TaskService(db).DeleteSubtask(task_id, subtask_id, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res