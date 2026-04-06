from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func, case
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.BadgeModel import Badge, UserBadge
from app.Objects.NewsModel import News
from app.Objects.UserModel import User
from app.Objects.finance.TransactionModel import Transaction, TransactionType
from app.Objects.tasks.TaskModel import Task, TaskStatus
from app.Objects.tasks.SubtaskModel import SubtaskStatus
from app.Objects.tasks.TaskTags import TaskTag
from app.Services.Hub.AuthService.depends import getuser

dashboard_router = APIRouter(prefix="/Dashboard", tags=["Hub > UserMe > Dashboard"])


@dashboard_router.get("/Get")
async def get_dashboard(
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    # 1. My active tasks
    tasks_query = (
        select(Task)
        .options(selectinload(Task.board), selectinload(Task.subtasks))
        .where(Task.assignee_ids.any(user.id))
        .where(Task.is_archived == False)
        .where(Task.is_removed == False)
        .where(Task.status.in_([TaskStatus.backlog, TaskStatus.in_progress, TaskStatus.review]))
        .order_by(Task.created_at.desc())
    )
    tasks_result = await db.execute(tasks_query)
    tasks_raw = tasks_result.scalars().all()

    tag_ids = set()
    for t in tasks_raw:
        if t.tags:
            tag_ids.update(t.tags)

    tags_dict = {}
    if tag_ids:
        tags_result = await db.execute(select(TaskTag).where(TaskTag.id.in_(tag_ids)))
        for tag in tags_result.scalars().all():
            tags_dict[tag.id] = {"id": str(tag.id), "name": tag.name, "color": tag.color}

    tasks = []
    for t in tasks_raw:
        task_tags = [tags_dict[tid] for tid in (t.tags or []) if tid in tags_dict]
        subtasks_total = len(t.subtasks) if t.subtasks else 0
        subtasks_completed = sum(1 for s in t.subtasks if s.status == SubtaskStatus.COMPLETED.value) if t.subtasks else 0
        tasks.append({
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

    # 2. Leaderboard
    total_earnings_expr = func.coalesce(
        func.sum(case(
            ((Transaction.is_removed == False) &
             Transaction.type.in_([TransactionType.INCOME, TransactionType.TRANSFER]) &
             (func.date_trunc("month", Transaction.transaction_at) == func.date_trunc("month", datetime.utcnow())),
             Transaction.amount),
            else_=0.0
        )), 0.0
    )
    lb_result = await db.execute(
        select(
            User.id, User.first_name, User.last_name, User.avatar_url,
            User.active_badge_emoji, total_earnings_expr.label("total_earnings")
        )
        .outerjoin(Transaction, Transaction.user_id == User.id)
        .where(User.is_active == True)
        .group_by(User.id)
        .having((total_earnings_expr > 0) | (User.id == user.id))
        .order_by(total_earnings_expr.desc())
    )
    leaderboard = [
        {
            "user_id": str(r.id), "first_name": r.first_name, "last_name": r.last_name,
            "avatar_url": r.avatar_url, "active_badge_emoji": r.active_badge_emoji,
            "total_earnings": float(r.total_earnings),
        }
        for r in lb_result.all()
    ]

    # 3. Recent badge awards
    awards_result = await db.execute(
        select(UserBadge, Badge, User)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .join(User, UserBadge.user_id == User.id)
        .order_by(UserBadge.awarded_at.desc())
        .limit(20)
    )
    badge_awards = [
        {
            "user_id": str(u.id),
            "user_name": f"{u.first_name} {u.last_name or ''}".strip(),
            "user_avatar": u.avatar_url,
            "badge_name": badge.name,
            "badge_description": badge.description,
            "badge_emoji": badge.emoji,
            "awarded_at": str(ub.awarded_at) if ub.awarded_at else None,
        }
        for ub, badge, u in awards_result.all()
    ]

    # 4. News
    news_result = await db.execute(select(News).order_by(desc(News.created_at)))
    news_items = []
    for n in news_result.scalars().all():
        author = await db.get(User, n.author_id)
        news_items.append({
            "id": str(n.id),
            "title": n.title,
            "content": n.content,
            "labels": n.labels or [],
            "target_text": n.target_text,
            "target_url": n.target_url,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "author": {
                "id": str(author.id),
                "first_name": author.first_name,
                "last_name": author.last_name,
                "avatar_url": author.avatar_url,
                "active_badge_emoji": author.active_badge_emoji,
            } if author else None,
        })

    return {
        "tasks": tasks,
        "leaderboard": leaderboard,
        "badge_awards": badge_awards,
        "news": news_items,
    }
