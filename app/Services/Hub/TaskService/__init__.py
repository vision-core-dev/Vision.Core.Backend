import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.LogModel import ActionType
from app.Objects.tasks.BoardModel import Board
from app.Objects.tasks.BoardListModel import BoardList
from app.Objects.tasks.SubtaskModel import Subtask, SubtaskBase, SubtaskStatus
from app.Objects.tasks.TaskAttachment import TaskAttachment, TaskComment
from app.Objects.tasks.TaskModel import Task, TaskStatus
from app.Objects.tasks.TaskTags import TaskTag
from app.Objects.UserModel import User
from app.Objects.finance.TaskAccrualModel import TaskAccrual
from app.Services.Hub.TaskService.contracts import (
    TaskDetailsResponse, UserPreview, TagPreview, AttachmentPreview, CommentPreview, AccrualPreview
)
from app.Services.Hub.NotifyService import NotifyService
from app.Services.LogService import LogService


class TaskService:
    def __init__(self, db):
        self.db = db
        self._notify = NotifyService(db)

    async def GetTaskDetails(self, task_id: uuid.UUID, user: User) -> TaskDetailsResponse:
        # 🔹 1. Отримуємо задачу
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # 🔹 3. Теги
        tag_list = []
        if task.tags:
            q_tags = await self.db.execute(select(TaskTag).where(TaskTag.id.in_(task.tags)))
            tag_list = [
                TagPreview(id=t.id, name=t.name, color=t.color)
                for t in q_tags.scalars().all()
            ]

        # 🔹 4. Виконавці
        assignee_users = []
        if task.assignee_ids:
            q_users = await self.db.execute(select(User).where(User.id.in_(task.assignee_ids)))
            assignee_users = [
                UserPreview(
                    id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    avatar_url=u.avatar_url
                )
                for u in q_users.scalars().all()
            ]

        # 🔹 5. Вкладення
        attachments_result = await self.db.execute(
            select(TaskAttachment).where(TaskAttachment.task_id == task.id)
        )
        attachments = [
            AttachmentPreview(
                id=a.id,
                type=a.type.value if hasattr(a.type, "value") else str(a.type),
                url=a.url,
                name=a.name,
                created_at=a.created_at,
            )
            for a in attachments_result.scalars().all()
        ]

        # subtasks
        q_subtasks = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task.id).order_by(Subtask.created_at)
        )
        subtasks = [
            SubtaskBase(
                id=s.id,
                name=s.name,
                status=s.status,
                deadline_at=s.deadline_at,
                assignee_id=s.assignee_id,
            )
            for s in q_subtasks.scalars().all()
        ]

        # 🔹 6. Коментарі
        comments_result = await self.db.execute(
            select(TaskComment).where(TaskComment.task_id == task.id).order_by(TaskComment.created_at)
        )
        comments = []
        for c in comments_result.scalars().all():
            user = await self.db.get(User, c.user_id)
            if not user:
                continue
            comments.append(
                CommentPreview(
                    id=c.id,
                    user=UserPreview(
                        id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        avatar_url=user.avatar_url
                    ),
                    content=c.content,
                    created_at=c.created_at
                )
            )

        # 🔹 7. Автор
        creator = await self.db.get(User, task.created_by_id)
        if not creator:
            raise HTTPException(status_code=404, detail="creator_not_found")

        # 🔹 Accruals (виплати по задачі)
        accruals_result = await self.db.execute(
            select(TaskAccrual).where(
                TaskAccrual.task_id == task.id,
                TaskAccrual.is_removed == False
            ).order_by(TaskAccrual.created_at)
        )
        accruals_list = []
        for acc in accruals_result.scalars().all():
            acc_user = await self.db.get(User, acc.user_id)
            if not acc_user:
                continue
            accruals_list.append(
                AccrualPreview(
                    id=acc.id,
                    user=UserPreview(
                        id=acc_user.id,
                        first_name=acc_user.first_name,
                        last_name=acc_user.last_name,
                        avatar_url=acc_user.avatar_url,
                    ),
                    name=acc.name,
                    amount=float(acc.amount),
                    created_at=acc.created_at,
                )
            )

        # ✅ 8. Формуємо фінальну відповідь
        return TaskDetailsResponse(
            id=task.id,
            list_id=task.list_id,
            name=task.name,
            description=task.description,
            banner_url=task.banner_url,
            tags=tag_list,
            assignees=assignee_users,
            started_at=task.started_at,
            deadline_at=task.deadline_at,
            completed_at=task.completed_at,
            attachments=attachments,
            subtasks=subtasks,
            accruals=accruals_list,
            comments=comments,
            created_by=UserPreview(
                id=creator.id,
                first_name=creator.first_name,
                last_name=creator.last_name,
                avatar_url=creator.avatar_url
            ),
            created_at=task.created_at
        )

    async def GetPublicTaskDetails(self, task_id: uuid.UUID):
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()

        task_board = await self.db.get(Board, task.board_id)
        if not task_board:
            raise HTTPException(status_code=404, detail="task_board_not_found")

        if task_board.is_public == False:
            raise HTTPException(status_code=403, detail="task_board_not_public")

        # 🔹 3. Теги
        tag_list = []
        if task.tags:
            q_tags = await self.db.execute(select(TaskTag).where(TaskTag.id.in_(task.tags)))
            tag_list = [
                TagPreview(id=t.id, name=t.name, color=t.color)
                for t in q_tags.scalars().all()
            ]

        # 🔹 4. Виконавці
        assignee_users = []
        if task.assignee_ids:
            q_users = await self.db.execute(select(User).where(User.id.in_(task.assignee_ids)))
            assignee_users = [
                UserPreview(
                    id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    avatar_url=u.avatar_url
                )
                for u in q_users.scalars().all()
            ]

        # 🔹 5. Вкладення
        attachments_result = await self.db.execute(
            select(TaskAttachment).where(TaskAttachment.task_id == task.id)
        )
        attachments = [
            AttachmentPreview(
                id=a.id,
                type=a.type.value if hasattr(a.type, "value") else str(a.type),
                url=a.url,
                name=a.name,
                created_at=a.created_at,
            )
            for a in attachments_result.scalars().all()
        ]

        # subtasks
        q_subtasks = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task.id).order_by(Subtask.created_at)
        )
        subtasks = [
            SubtaskBase(
                id=s.id,
                name=s.name,
                status=s.status,
                deadline_at=s.deadline_at,
                assignee_id=s.assignee_id,
            )
            for s in q_subtasks.scalars().all()
        ]

        # 🔹 6. Коментарі
        comments_result = await self.db.execute(
            select(TaskComment).where(TaskComment.task_id == task.id).order_by(TaskComment.created_at)
        )
        comments = []
        for c in comments_result.scalars().all():
            user = await self.db.get(User, c.user_id)
            if not user:
                continue
            comments.append(
                CommentPreview(
                    id=c.id,
                    user=UserPreview(
                        id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        avatar_url=user.avatar_url
                    ),
                    content=c.content,
                    created_at=c.created_at
                )
            )

        # 🔹 7. Автор
        creator = await self.db.get(User, task.created_by_id)
        if not creator:
            raise HTTPException(status_code=404, detail="creator_not_found")

        # 🔹 Accruals (виплати по задачі)
        accruals_result = await self.db.execute(
            select(TaskAccrual).where(
                TaskAccrual.task_id == task.id,
                TaskAccrual.is_removed == False
            ).order_by(TaskAccrual.created_at)
        )
        accruals_list = []
        for acc in accruals_result.scalars().all():
            acc_user = await self.db.get(User, acc.user_id)
            if not acc_user:
                continue
            accruals_list.append(
                AccrualPreview(
                    id=acc.id,
                    user=UserPreview(
                        id=acc_user.id,
                        first_name=acc_user.first_name,
                        last_name=acc_user.last_name,
                        avatar_url=acc_user.avatar_url,
                    ),
                    name=acc.name,
                    amount=float(acc.amount),
                    created_at=acc.created_at,
                )
            )

        # ✅ 8. Формуємо фінальну відповідь
        return TaskDetailsResponse(
            id=task.id,
            list_id=task.list_id,
            name=task.name,
            description=task.description,
            banner_url=task.banner_url,
            tags=tag_list,
            assignees=assignee_users,
            started_at=task.started_at,
            deadline_at=task.deadline_at,
            completed_at=task.completed_at,
            attachments=attachments,
            subtasks=subtasks,
            accruals=accruals_list,
            comments=comments,
            created_by=UserPreview(
                id=creator.id,
                first_name=creator.first_name,
                last_name=creator.last_name,
                avatar_url=creator.avatar_url
            ),
            created_at=task.created_at
        )


    # ✅ Призначити користувача
    async def AssignUser(self, task_id: uuid.UUID, user_id: uuid.UUID, current_user: User = None):
        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        current_ids = set(task.assignee_ids or [])
        if user_id in current_ids:
            return {"ok": True, "message": "already_assigned"}

        old_assignees = list(current_ids)
        current_ids.add(user_id)
        new_assignees = list(current_ids)
        
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(assignee_ids=new_assignees)
        )

        # Сповіщення призначеному
        if not current_user or user_id != current_user.id:
            await self._notify.CreateNotification(
                user_id=user_id,
                title="👤 Призначення на задачу",
                message=f"Вас призначено на задачу <b>{task.name}</b>",
                link=f"/boards/b/{task.board_id}/t/{task_id}",
            )

        await self.db.commit()

        # Логування
        await LogService.log_action(
            db=self.db,
            actor_id=current_user.id if current_user else None,
            entity_type="Task",
            entity_id=task_id,
            entity_name=task.name,
            action=ActionType.ASSIGN,
            details=f"Призначено користувача {user_id} на задачу",
            extra_data={
                "assigned_user_id": str(user_id),
                "old_assignees": [str(uid) for uid in old_assignees],
                "new_assignees": [str(uid) for uid in new_assignees],
            }
        )

        return {"ok": True, "board_id": str(task.board_id)}

    # ❌ Зняти користувача
    async def UnassignUser(self, task_id: uuid.UUID, user_id: uuid.UUID):
        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        current_ids = set(task.assignee_ids or [])
        if user_id not in current_ids:
            return {"ok": True, "message": "not_assigned"}

        current_ids.remove(user_id)
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(assignee_ids=list(current_ids))
        )

        await self._notify.CreateNotification(
            user_id=user_id,
            title="🚫 Зняття з задачі",
            message=f"Вас знято з задачі <b>{task.name}</b>",
            link=f"/boards/b/{task.board_id}/t/{task_id}",
        )

        await self.db.commit()
        return {"ok": True, "board_id": str(task.board_id)}

    # 🏷️ Додати мітку
    async def AssignTag(self, task_id: uuid.UUID, tag_id: uuid.UUID):
        tag = await self.db.get(TaskTag, tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="tag_not_found")

        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        current_tags = set(task.tags or [])
        if tag_id in current_tags:
            return {"ok": True, "message": "already_tagged"}

        current_tags.add(tag_id)
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(tags=list(current_tags))
        )
        await self.db.commit()
        return {"ok": True, "board_id": str(task.board_id)}

    # ❌ Зняти мітку
    async def UnassignTag(self, task_id: uuid.UUID, tag_id: uuid.UUID):
        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        current_tags = set(task.tags or [])
        if tag_id not in current_tags:
            return {"ok": True, "message": "not_tagged"}

        current_tags.remove(tag_id)
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(tags=list(current_tags))
        )
        await self.db.commit()
        return {"ok": True, "board_id": str(task.board_id)}


    async def ArchiveTask(self, task_id: uuid.UUID, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ⚙️ Позначаємо як архівовану
        task.is_archived = True
        await self.db.commit()
        
        # Логування
        await LogService.log_action(
            db=self.db,
            actor_id=user.id if user else None,
            entity_type="Task",
            entity_id=task_id,
            entity_name=task.name,
            action=ActionType.ARCHIVE,
            details=f"Задачу '{task.name}' заархівовано",
        )

        return {
            "ok": True,
            "message": f"Task {task.name} archived successfully",
            "task_id": str(task.id),
            "board_id": str(task.board_id)
        }


    async def UpdateTaskDescription(self, task_id: uuid.UUID, description: str, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ✏️ Оновлюємо опис
        task.description = description
        await self.db.commit()

        return {
            "ok": True,
            "message": f"Task {task.name} description updated successfully",
            "task_id": str(task.id),
            "board_id": str(task.board_id)
        }

    async def UpdateTaskName(self, task_id: uuid.UUID, name: str, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # Зберігаємо стару назву для логування
        old_name = task.name
        
        # ✏️ Оновлюємо назву
        task.name = name
        await self.db.commit()
        
        # Логування
        await LogService.log_update(
            db=self.db,
            actor_id=user.id if user else None,
            entity_type="Task",
            entity_id=task_id,
            entity_name=name,
            old_values={"name": old_name},
            new_values={"name": name},
            changed_fields=["name"],
            details=f"Назву задачі змінено з '{old_name}' на '{name}'",
        )

        return {
            "ok": True,
            "message": f"Task name updated successfully",
            "task_id": str(task.id),
            "board_id": str(task.board_id)
        }


    async def AddLinkAttachment(self, task_id, url, name, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        name = name or url

        # 🗂️ Створюємо вкладення
        attachment = TaskAttachment(
            task_id=task.id,
            type="link",
            url=url,
            name=name
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        return {
            "ok": True,
            "message": "Attachment added successfully",
            "id": str(attachment.id),
            "name": attachment.name,
            "url": attachment.url
        }

    async def UploadFileAttachment(self, task_id, file, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        contents = await file.read()
        filename = f"uploads/{user.id}_{uuid.uuid4()}_{file.filename}"

        file_url = await _upload_to_bunny(filename, contents, file.content_type)

        # 🗂️ Створюємо вкладення
        attachment = TaskAttachment(
            task_id=task.id,
            type="file",
            url=file_url,  # Тут має бути логіка збереження файлу
            name=file.filename
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)

        return {
            "ok": True,
            "message": "Attachment uploaded successfully",
            "id": str(attachment.id),
            "name": attachment.name,
            "url": attachment.url
        }

    async def RenameAttachment(self, task_id, attachment_id, new_name, user):
        # 🔍 Знайти вкладення
        attachment = await self.db.get(TaskAttachment, attachment_id)
        if not attachment or attachment.task_id != task_id:
            raise HTTPException(status_code=404, detail="attachment_not_found")

        # ✏️ Оновлюємо назву
        attachment.name = new_name
        await self.db.commit()

        return {
            "ok": True,
            "message": "Attachment renamed successfully",
            "attachment_id": str(attachment.id),
            "new_name": attachment.name
        }

    async def RemoveAttachment(self, task_id, attachment_id, user):
        # 🔍 Знайти вкладення
        attachment = await self.db.get(TaskAttachment, attachment_id)
        if not attachment or attachment.task_id != task_id:
            raise HTTPException(status_code=404, detail="attachment_not_found")

        # ❌ Видаляємо вкладення
        await self.db.delete(attachment)
        await self.db.commit()

        return {
            "ok": True,
            "message": "Attachment removed successfully",
            "attachment_id": str(attachment.id)
        }

    async def UploadTaskBanner(self, task_id, file, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        contents = await file.read()
        filename = f"banners/{task_id}_{uuid.uuid4()}_{file.filename}"

        banner_url = await _upload_to_bunny(filename, contents, file.content_type)

        task.banner_url = banner_url
        await self.db.commit()

        return {
            "ok": True,
            "message": "Task banner uploaded successfully",
            "banner_url": banner_url
        }

    async def SetTaskBanner(self, task_id, banner_url, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # Оновлюємо банер
        task.banner_url = banner_url
        await self.db.commit()

        return {
            "ok": True,
            "message": "Task banner updated successfully",
            "banner_url": task.banner_url
        }

    async def MoveTaskToList(self, task_id, list_id, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        old_list_id = task.list_id

        # Оновлюємо список
        task.list_id = list_id

        # Сповіщення якщо список змінився
        if str(old_list_id) != str(list_id) and task.assignee_ids:
            new_list = await self.db.get(BoardList, list_id)
            list_name = new_list.name if new_list else "інший список"
            for uid in task.assignee_ids:
                await self._notify.CreateNotification(
                    user_id=uid,
                    title="📋 Задачу переміщено",
                    message=f"Задачу <b>{task.name}</b> переміщено в <b>{list_name}</b>",
                    link=f"/boards/b/{task.board_id}/t/{task_id}",
                )

        await self.db.commit()

        return {
            "ok": True,
            "message": "Task moved to new list successfully",
            "list_id": str(task.list_id),
            "board_id": str(task.board_id)
        }

    async def SetTaskOrder(self, task_id: uuid.UUID, order: int | None, list_id: uuid.UUID, user):
        # 🔍 Знаходимо задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # 🔍 Отримуємо всі задачі у цільовому списку
        result = await self.db.execute(
            select(Task).where(Task.list_id == list_id).order_by(Task.order.asc())
        )
        tasks = result.scalars().all()

        # 🧮 Обчислюємо новий order
        if not tasks:
            new_order = 1000  # якщо список порожній
        elif order is None or order >= len(tasks):
            # додаємо в кінець
            new_order = tasks[-1].order + 1000
        elif order <= 0:
            # додаємо на початок
            new_order = tasks[0].order - 1000
        else:
            # між задачами
            prev_task = tasks[order - 1]
            next_task = tasks[order]
            new_order = (prev_task.order + next_task.order) / 2

        # 🧩 Оновлюємо задачу
        task.order = new_order
        task.list_id = list_id
        await self.db.commit()

        return {
            "ok": True,
            "message": "Task reordered successfully",
            "task_id": str(task.id),
            "new_order": new_order,
            "board_id": str(task.board_id)
        }

    async def UpdateTaskDates(self, task_id, deadline_at, started_at, completed_at, user):
        # 🔍 Знаходимо задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # 🧭 Функція для безпечної конвертації
        def parse_date(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                # ⏰ datetime-local -> datetime object
                return datetime.fromisoformat(value)
            except Exception:
                return None

        # 🗓️ Конвертуємо в datetime перед оновленням
        started_at_dt = parse_date(started_at)
        deadline_at_dt = parse_date(deadline_at)
        completed_at_dt = parse_date(completed_at)

        old_deadline = task.deadline_at

        # 🧮 Оновлюємо дати
        if started_at_dt is not None:
            task.started_at = started_at_dt
        if deadline_at_dt is not None:
            task.deadline_at = deadline_at_dt
        if completed_at_dt is not None:
            task.completed_at = completed_at_dt

        # Сповіщення про зміну дедлайну
        if deadline_at_dt and deadline_at_dt != old_deadline and task.assignee_ids:
            dl = deadline_at_dt.strftime("%d.%m.%Y %H:%M")
            for uid in task.assignee_ids:
                await self._notify.CreateNotification(
                    user_id=uid,
                    title="📅 Зміна дедлайну",
                    message=f"Дедлайн задачі <b>{task.name}</b> змінено на {dl}",
                    link=f"/boards/b/{task.board_id}/t/{task.id}",
                )

        await self.db.commit()

        return {
            "ok": True,
            "message": "Task dates updated successfully",
            "task_id": str(task.id),
            "deadline_at": task.deadline_at,
            "started_at": task.started_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "board_id": str(task.board_id)
        }

    async def GetSubtasks(self, task_id, user):

        # 🔍 Знаходимо задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # 📋 Отримуємо підзадачі
        result = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task_id).order_by(Subtask.created_at)
        )
        subtasks = result.scalars().all()
        return subtasks

    async def CreateSubtask(self, task_id, name, user):
        # 🔍 Знаходимо задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ➕ Створюємо підзадачу
        subtask = Subtask(
            name=name,
            task_id=task_id
        )
        self.db.add(subtask)
        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def RenameSubtask(self, task_id, subtask_id, new_name, user):
        # 🔍 Знаходимо підзадачу
        subtask = await self.db.get(Subtask, subtask_id)
        if not subtask or subtask.task_id != task_id:
            raise HTTPException(status_code=404, detail="subtask_not_found")

        # ✏️ Оновлюємо назву
        subtask.name = new_name
        await self.db.commit()

        task = await self.db.get(Task, task_id)
        return {
            "subtask_id": str(subtask.id),
            "new_name": subtask.name,
            "board_id": str(task.board_id) if task else None
        }

    async def SetSubtaskCompleted(self, task_id, subtask_id, is_completed: bool, user):
        # 🔍 Знаходимо підзадачу
        subtask = await self.db.get(Subtask, subtask_id)
        if not subtask or subtask.task_id != task_id:
            raise HTTPException(status_code=404, detail="subtask_not_found")

        # ✅ Оновлюємо статус підзадачі
        subtask.status = SubtaskStatus.COMPLETED.value if is_completed else SubtaskStatus.IN_PROGRESS.value
        await self.db.flush()

        # 🔍 Завантажуємо всі підзадачі задачі
        subtasks = (
            await self.db.execute(
                select(Subtask).where(Subtask.task_id == task_id)
            )
        ).scalars().all()

        # 👀 Перевіряємо чи всі виконані
        all_done = all(s.status == SubtaskStatus.COMPLETED.value for s in subtasks)

        # 🔍 Завантажуємо задачу
        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        was_done = task.status == TaskStatus.done

        # 🎯 Оновлюємо статус задачі залежно від підзадач
        if all_done:
            task.status = TaskStatus.done
            task.completed_at = func.now()

            # Сповіщення про завершення задачі
            if task.assignee_ids:
                for uid in task.assignee_ids:
                    await self._notify.CreateNotification(
                        user_id=uid,
                        title="✅ Задачу завершено",
                        message=f"Усі підзадачі <b>{task.name}</b> виконано",
                        link=f"/boards/b/{task.board_id}/t/{task.id}",
                    )
        else:
            task.status = TaskStatus.in_progress
            task.completed_at = None

            # Сповіщення якщо задачу повернули з done
            if was_done and task.assignee_ids:
                for uid in task.assignee_ids:
                    await self._notify.CreateNotification(
                        user_id=uid,
                        title="🔄 Задачу відновлено",
                        message=f"Задачу <b>{task.name}</b> повернуто в роботу",
                        link=f"/boards/b/{task.board_id}/t/{task.id}",
                    )

        await self.db.commit()

        return {
            "subtask_id": str(subtask.id),
            "subtask_status": subtask.status,
            "task_status": task.status.value,
            "board_id": str(task.board_id)
        }

    async def DeleteSubtask(self, task_id, subtask_id, user):
        # 🔍 Знаходимо підзадачу
        subtask = await self.db.get(Subtask, subtask_id)
        if not subtask or subtask.task_id != task_id:
            raise HTTPException(status_code=404, detail="subtask_not_found")

        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ❌ Видаляємо підзадачу
        await self.db.delete(subtask)
        await self.db.flush()  # 👈 не коммітимо тут

        # ♻️ Отримуємо оновлений список підзадач через SELECT
        result = await self.db.execute(
            select(Subtask).where(Subtask.task_id == task_id)
        )
        remaining_subtasks = result.scalars().all()

        # 🎯 Перераховуємо статус задачі
        if len(remaining_subtasks) == 0:
            task.status = TaskStatus.in_progress
            task.completed_at = None
        else:
            completed_count = sum(1 for s in remaining_subtasks if s.status == "completed")
            if completed_count == len(remaining_subtasks):
                task.status = TaskStatus.done
                task.completed_at = func.now()
            else:
                task.status = TaskStatus.in_progress
                task.completed_at = None

        await self.db.commit()

        return {
            "subtask_id": str(subtask_id),
            "task_status": task.status.value,
            "total_subtasks": len(remaining_subtasks),
            "board_id": str(task.board_id)
        }
