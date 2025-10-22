import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser
from app.Objects.UserModel import User
from app.Services.Hub.TaskService import TaskService
from app.Services.Hub.TaskService.contracts import TaskDetailsResponse

tasks_router = APIRouter(prefix="/Tasks")

@tasks_router.get("/{task_id}/GetDetails", response_model=TaskDetailsResponse)
async def get_task_details(task_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await TaskService(db).GetTaskDetails(task_id, user)
