import asyncio
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.NotifyModel import UserNotify, MyNotifyBase
from app.Objects.UserModel import User
from app.Services.Hub.NotifyService.contracts import NotifiesListResponse, UnreadNotifiesCountResponse
from app.Services.Hub.NotifyService.external import send_telegram_notification, send_discord_notification


class NotifyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def GetNotifiesList(self, user: User) -> NotifiesListResponse:
        """
        Отримати список сповіщень користувача (новіші першими)
        """
        result = await self.db.execute(
            select(UserNotify)
            .where(UserNotify.user_id == user.id)
            .order_by(UserNotify.created_at.desc())
        )
        notifs = result.scalars().all()
        return NotifiesListResponse(total=len(notifs), list=[MyNotifyBase.model_validate(n) for n in notifs])

    async def GetUnreadNotifiesCount(self, user: User) -> UnreadNotifiesCountResponse:
        """
        Отримати кількість непрочитаних сповіщень користувача
        """
        result = await self.db.execute(
            select(UserNotify)
            .where(UserNotify.user_id == user.id, UserNotify.is_read == False)
        )
        notifs = result.scalars().all()
        return UnreadNotifiesCountResponse(count=len(notifs))

    async def MarkNotificationAsRead(self, user: User, notify_id):
        """
        Позначити одне сповіщення як переглянуте
        """
        stmt = (
            update(UserNotify)
            .where(UserNotify.id == notify_id, UserNotify.user_id == user.id)
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
            update(UserNotify)
            .where(UserNotify.user_id == user.id)
            .values(is_read=True)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return {"status": "ok", "message": "Усі сповіщення позначені як переглянуті"}

    async def CreateNotification(self, user_id: uuid.UUID, title: str, message: str, link: str = None):
        """
        Створити нове сповіщення для користувача + відправити в Discord/Telegram
        """
        new_notif = UserNotify(
            user_id=user_id,
            title=title,
            message=message,
            link=link,
        )
        self.db.add(new_notif)

        # Dispatch to external channels
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            tasks = []
            if user.notify_telegram and user.telegram_id:
                tasks.append(send_telegram_notification(user.telegram_id, title, message, link))
            if user.notify_discord and user.discord_id:
                tasks.append(send_discord_notification(user.discord_id, title, message, link))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
