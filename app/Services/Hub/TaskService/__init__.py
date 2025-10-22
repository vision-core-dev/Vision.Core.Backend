import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.Objects.tasks.TaskAttachment import TaskAttachment, TaskComment
from app.Objects.tasks.TaskModel import Task
from app.Objects.tasks.TaskTags import TaskTag
from app.Objects.tasks.TaskModel import TaskAssignee
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
            .options(selectinload(Task.assignees))
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="task_not_found")

        # 🔹 2. Отримуємо банер (через banner_attachment_id)
        banner_url = None
        if task.banner_attachment_id:
            banner = await self.db.get(TaskAttachment, task.banner_attachment_id)
            if banner:
                banner_url = banner.url

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
        if task.assignees:
            user_ids = [a.user_id for a in task.assignees]
            q_users = await self.db.execute(select(User).where(User.id.in_(user_ids)))
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
            banner_url=banner_url,
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
