from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.NotificationModel import UserNotif, MyNotifBase
from app.Objects.UserModel import User
from app.Services.Hub.NotifyService.contracts import NotifiesListResponse, UnreadNotifiesCountResponse


class NotifyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def GetNotifiesList(self, user: User) -> NotifiesListResponse:
        """
        Отримати список сповіщень користувача (новіші першими)
        """
        result = await self.db.execute(
            select(UserNotif)
            .where(UserNotif.user_id == user.id)
            .order_by(UserNotif.created_at.desc())
        )
        notifs = result.scalars().all()
        return NotifiesListResponse(total=len(notifs), list=[MyNotifBase.model_validate(n) for n in notifs])

    async def GetUnreadNotifiesCount(self, user: User) -> UnreadNotifiesCountResponse:
        """
        Отримати кількість непрочитаних сповіщень користувача
        """
        result = await self.db.execute(
            select(UserNotif)
            .where(UserNotif.user_id == user.id, UserNotif.is_read == False)
        )
        notifs = result.scalars().all()
        return UnreadNotifiesCountResponse(count=len(notifs))

    async def MarkNotificationAsRead(self, user: User, notify_id):
        """
        Позначити одне сповіщення як переглянуте
        """
        stmt = (
            update(UserNotif)
            .where(UserNotif.id == notify_id, UserNotif.user_id == user.id)
            .values(is_read=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return {"status": "ok", "message": "Сповіщення позначене як переглянуте"}

    async def MarkAllNotificationsAsRead(self, user: User):
        """
        Позначити всі сповіщення користувача як переглянуті
        """
        stmt = (
            update(UserNotif)
            .where(UserNotif.user_id == user.id)
            .values(is_read=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return {"status": "ok", "message": "Усі сповіщення позначені як переглянуті"}
