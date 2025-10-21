from fastapi import APIRouter
from fastapi.params import Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.EventModel import EventPreview
from app.Objects.UserModel import User
from app.Objects.tasks.TaskModel import TaskPreview
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.EventService import EventService

my_calendar_router = APIRouter()

class MyCalendarResponse(BaseModel):
    events: list[EventPreview]
    tasks: list[TaskPreview]




@my_calendar_router.get("/MyCalendar", response_model=MyCalendarResponse)
async def my_calendar(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    events = await EventService(db).GetUserEventsList(user)
    # tasks = await TaskService(db).GetUserTasks(user)
    return MyCalendarResponse(events=events, tasks=[])