import uuid
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.tasks.TaskModel import Task, TaskStatus
from app.Objects.tasks.SubtaskModel import SubtaskStatus
from app.Objects.tasks.TaskTags import TaskTag
from app.Services.Hub.AuthService.depends import getuser

my_tasks_router = APIRouter(prefix="/Tasks", tags=["Hub > UserMe > Tasks"])

@my_tasks_router.get("/Active")
async def get_my_active_tasks(
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    query = (
        select(Task)
        .options(selectinload(Task.board), selectinload(Task.subtasks))
        .where(Task.assignee_ids.any(user.id))
        .where(Task.is_archived == False)
        .where(Task.is_removed == False)
        .where(Task.status.in_([TaskStatus.backlog, TaskStatus.in_progress, TaskStatus.review]))
        .order_by(Task.created_at.desc())
    )
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    tag_ids = set()
    for t in tasks:
        if t.tags:
            tag_ids.update(t.tags)
    
    tags_dict = {}
    if tag_ids:
        tags_result = await db.execute(select(TaskTag).where(TaskTag.id.in_(tag_ids)))
        for tag in tags_result.scalars().all():
            tags_dict[tag.id] = {"id": str(tag.id), "name": tag.name, "color": tag.color}
    
    out = []
    for t in tasks:
        task_tags = [tags_dict[tag_id] for tag_id in (t.tags or []) if tag_id in tags_dict]
        
        subtasks_total = len(t.subtasks) if t.subtasks else 0
        subtasks_completed = sum(1 for s in t.subtasks if s.status == SubtaskStatus.COMPLETED.value) if t.subtasks else 0
        
        out.append({
            "id": str(t.id),
            "name": t.name,
            "board_id": str(t.board_id) if t.board_id else None,
            "board_name": t.board.name if t.board else None,
            "list_id": str(t.list_id) if t.list_id else None,
            "status": t.status.value,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "deadline_at": t.deadline_at.isoformat() if t.deadline_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "tags": task_tags,
            "subtasks_total": subtasks_total,
            "subtasks_completed": subtasks_completed,
        })

    return out
