import uuid
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.tasks.TaskAttachment import TaskAttachment, TaskComment
from app.Objects.tasks.TaskModel import Task
from app.Objects.tasks.TaskTags import TaskTag
from app.Objects.UserModel import User
from app.Services.Hub.TaskService.contracts import (
    TaskDetailsResponse, UserPreview, TagPreview, AttachmentPreview, CommentPreview
)


class TaskService:
    def __init__(self, db):
        self.db = db

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
                name=a.name
            )
            for a in attachments_result.scalars().all()
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

        # ✅ 8. Формуємо фінальну відповідь
        return TaskDetailsResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            banner_url=task.banner_url,
            tags=tag_list,
            assignees=assignee_users,
            attachments=attachments,
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
    async def AssignUser(self, task_id: uuid.UUID, user_id: uuid.UUID):
        task = await self.db.get(Task, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        current_ids = set(task.assignee_ids or [])
        if user_id in current_ids:
            return {"ok": True, "message": "already_assigned"}

        current_ids.add(user_id)
        await self.db.execute(
            update(Task).where(Task.id == task_id).values(assignee_ids=list(current_ids))
        )
        await self.db.commit()
        return {"ok": True}

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
        await self.db.commit()
        return {"ok": True}

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
        return {"ok": True}

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
        return {"ok": True}


    async def ArchiveTask(self, task_id: uuid.UUID, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ⚙️ Позначаємо як архівовану
        task.is_archived = True
        await self.db.commit()

        return {
            "ok": True,
            "message": f"Task {task.name} archived successfully",
            "task_id": str(task.id)
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
            "task_id": str(task.id)
        }

    async def UpdateTaskName(self, task_id: uuid.UUID, name: str, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # ✏️ Оновлюємо назву
        task.name = name
        await self.db.commit()

        return {
            "ok": True,
            "message": f"Task name updated successfully",
            "task_id": str(task.id)
        }


    async def AddLinkAttachment(self, task_id, url, name, user):
        # 🔍 Знайти задачу
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

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
            "attachment_id": str(attachment.id),
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
            "attachment_id": str(attachment.id),
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
