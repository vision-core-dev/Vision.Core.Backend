from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.NotifyService import NotifyService, NotifiesListResponse, UnreadNotifiesCountResponse

notifies_router = APIRouter(prefix="/Notifies", tags=["Hub > UserMe > Notifies"])

@notifies_router.get("/List", response_model=NotifiesListResponse, dependencies=[Depends(HTTPBearer(auto_error=False))])
async def list_notifies(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await NotifyService(db).GetNotifiesList(user)

@notifies_router.post("/MarkAsRead/{notify_id}", dependencies=[Depends(HTTPBearer(auto_error=False))])
async def mark_notify_as_read(notify_id: str, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await NotifyService(db).MarkNotificationAsRead(user, notify_id)

@notifies_router.post("/MarkAllAsRead", dependencies=[Depends(HTTPBearer(auto_error=False))])
async def mark_all_notifies_as_read(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await NotifyService(db).MarkAllNotificationsAsRead(user)