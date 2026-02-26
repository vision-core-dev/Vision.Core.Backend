from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.NotifyService import NotifyService

user_me_router = APIRouter(prefix="/UserMe", tags=["Hub > UserMe"])


@user_me_router.get("/Get", dependencies=[Depends(HTTPBearer(auto_error=False))])
async def get_unread_notifies_count(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    unread_count = await NotifyService(db).GetUnreadNotifiesCount(user)

    return {"unread_count": unread_count.count, "balance_visible": user.is_balance_visible, "balance_uah": user.balance}


from .Notifies import notifies_router
user_me_router.include_router(notifies_router)

from .MyProfile import my_profile_router
user_me_router.include_router(my_profile_router)

from .MyTasks import my_tasks_router
user_me_router.include_router(my_tasks_router)