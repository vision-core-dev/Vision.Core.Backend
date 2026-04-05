"""
Periodic task to send deadline reminders (1 day and 1 hour before).
Called by APScheduler from main.py lifespan.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import async_session
from app.Objects.tasks.TaskModel import Task
from app.Objects.NotifyModel import UserNotify
from app.Services.Hub.NotifyService import NotifyService


async def check_deadline_reminders():
    async with async_session() as db:
        now = datetime.now(timezone.utc)

        # Windows: 1 day before and 1 hour before
        windows = [
            ("1 день", "📆", now + timedelta(hours=23, minutes=30), now + timedelta(hours=24, minutes=30)),
            ("1 година", "⏰", now + timedelta(minutes=30), now + timedelta(hours=1, minutes=30)),
        ]

        for label, emoji, window_start, window_end in windows:
            result = await db.execute(
                select(Task).where(
                    and_(
                        Task.deadline_at >= window_start,
                        Task.deadline_at <= window_end,
                        Task.status != "done",
                        Task.is_archived == False,
                        Task.is_removed == False,
                    )
                )
            )
            tasks = result.scalars().all()

            notify = NotifyService(db)
            for task in tasks:
                if not task.assignee_ids:
                    continue

                dl = task.deadline_at.strftime("%d.%m.%Y %H:%M")
                for uid in task.assignee_ids:
                    # Check if we already sent this reminder
                    existing = await db.execute(
                        select(UserNotify).where(
                            and_(
                                UserNotify.user_id == uid,
                                UserNotify.title == f"{emoji} Дедлайн через {label}",
                                UserNotify.link == f"/boards/b/{task.board_id}/t/{task.id}",
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    await notify.CreateNotification(
                        user_id=uid,
                        title=f"{emoji} Дедлайн через {label}",
                        message=f"Задача <b>{task.name}</b> — дедлайн {dl}",
                        link=f"/boards/b/{task.board_id}/t/{task.id}",
                    )

            await db.commit()
