import uuid

from sqlalchemy import select

from app.Objects.UserModel import User
from app.Objects.tasks.TaskModel import Task


class TaskService:
    def __init__(self, db):
        self.db = db

    async def CreateBoardTask(self, name: str, board_id: uuid.UUID, list_id: uuid.UUID, user: User):
        new_task = Task(
            name=name,
            created_by_id=user.id
        )
        self.db.add(new_task)
        await self.db.commit()
        await self.db.refresh(new_task)
        return new_task

    async def UpdateTaskField(self, task_id: uuid.UUID, field: str, value, user: User):
        """🔄 Безпечне оновлення тільки дозволених полів задачі"""

        # ✅ Явно вказуємо, що дозволено змінювати
        allowed_fields = {
            "list_id":  10,
            "order": 10,
            "name": 10,
            "description": 10,
            "deadline_at": 10,
            "status": 4,
            "priority": 4
        }

        if field not in allowed_fields:
            raise Exception(f"Field '{field}' is not allowed to be updated")

        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise Exception("Task not found")

        setattr(task, field, value)

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task
