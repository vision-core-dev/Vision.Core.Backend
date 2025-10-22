import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.BoardService import BoardService
from app.Services.Hub.BoardService.contracts import CreateTaskRequest, CreateTaskResponse

task_router = APIRouter(prefix="/Tasks")

@task_router.post("/Create", response_model=CreateTaskResponse)
async def create_task(
    board_id: uuid.UUID,
    data: CreateTaskRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await BoardService(db).CreateTask(
        board_id=board_id,
        list_id=data.list_id,
        name=data.name,
        description=data.description,
        assignee_ids=data.assignee_ids,
        priority=data.priority,
        deadline_at=data.deadline_at,
        value_uah=data.value_uah,
        created_by=user
    )