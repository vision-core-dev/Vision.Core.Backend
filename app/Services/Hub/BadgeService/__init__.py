from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload
from datetime import datetime
import uuid

from app.Objects.BadgeModel import Badge, UserBadge, UserBadgeBase


class BadgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def AwardBadge(self, user_id: uuid.UUID, badge_key: str):
        """
        🏅 Видати бейдж користувачу по badge_key (name або id).
        """
        # Знаходимо бейдж по name або id
        stmt = select(Badge).where(
            (Badge.id == badge_key) | (Badge.name == badge_key)
        )
        badge = (await self.db.execute(stmt)).scalar_one_or_none()
        if not badge:
            raise ValueError("❌ Бейдж не знайдено")

        # Перевіряємо, чи вже видано цей бейдж
        existing = await self.db.execute(
            select(UserBadge).where(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge.id
            )
        )
        if existing.scalar_one_or_none():
            return "⚠️ Користувач уже має цей бейдж"

        # Створюємо новий запис
        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge.id,
            awarded_at=datetime.utcnow()
        )
        self.db.add(user_badge)
        await self.db.commit()
        return "✅ Бейдж успішно видано"

    async def RevokeBadge(self, user_id: uuid.UUID, badge_key: str):
        """
        ❌ Відкликати бейдж у користувача.
        """
        # Знаходимо бейдж
        badge = (await self.db.execute(
            select(Badge).where(
                (Badge.id == badge_key) | (Badge.name == badge_key)
            )
        )).scalar_one_or_none()

        if not badge:
            raise ValueError("❌ Бейдж не знайдено")

        # Видаляємо зв'язок користувача і бейджа
        await self.db.execute(
            delete(UserBadge).where(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge.id
            )
        )
        await self.db.commit()
        return "🗑️ Бейдж відкликано"

    async def ListUserBadges(self, user_id: uuid.UUID) -> list[UserBadgeBase]:
        """
        📜 Повертає всі бейджі користувача з детальною інформацією.
        """
        stmt = (
            select(UserBadge, Badge)
            .join(Badge, UserBadge.badge_id == Badge.id)
            .where(UserBadge.user_id == user_id)
            .options(joinedload(UserBadge.badge_id))
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        badges = []
        for user_badge, badge in rows:
            badges.append(UserBadgeBase(
                id=badge.id,
                name=badge.name,
                description=badge.description,
                icon_url=badge.icon_url,
                emoji=badge.emoji,
                awarded_at=user_badge.awarded_at
            ))

        return badges
