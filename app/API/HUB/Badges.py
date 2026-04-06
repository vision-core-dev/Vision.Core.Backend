import uuid

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.BadgeModel import Badge, UserBadge, UserBadgeBase
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.BadgeService import BadgeService

badges_router = APIRouter(prefix="/Badges", tags=["Hub > Badges"])


# --- Badge CRUD ---

class CreateBadgeRequest(BaseModel):
    name: str
    description: str | None = None
    emoji: str | None = None
    icon_url: str | None = None


class BadgeResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    emoji: str | None
    icon_url: str | None

    class Config:
        from_attributes = True


@badges_router.get("/List")
async def list_badges(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(Badge).order_by(Badge.created_at))
    badges = result.scalars().all()
    return [BadgeResponse.model_validate(b) for b in badges]


@badges_router.post("/Create", response_model=BadgeResponse)
async def create_badge(data: CreateBadgeRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    badge = Badge(
        name=data.name,
        description=data.description,
        emoji=data.emoji,
        icon_url=data.icon_url,
    )
    db.add(badge)
    await db.commit()
    await db.refresh(badge)
    return BadgeResponse.model_validate(badge)


@badges_router.post("/{badge_id}/Update", response_model=BadgeResponse)
async def update_badge(badge_id: uuid.UUID, data: CreateBadgeRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="badge_not_found")

    badge.name = data.name
    badge.description = data.description
    badge.emoji = data.emoji
    badge.icon_url = data.icon_url
    await db.commit()
    await db.refresh(badge)
    return BadgeResponse.model_validate(badge)


@badges_router.post("/{badge_id}/Delete")
async def delete_badge(badge_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    badge = await db.get(Badge, badge_id)
    if not badge:
        raise HTTPException(status_code=404, detail="badge_not_found")

    await db.delete(badge)
    await db.commit()
    return {"ok": True}


# --- Recent Awards (for dashboard timeline) ---

@badges_router.get("/RecentAwards")
async def recent_awards(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    from app.Objects.UserModel import User as UserModel

    result = await db.execute(
        select(UserBadge, Badge, UserModel)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .join(UserModel, UserBadge.user_id == UserModel.id)
        .order_by(UserBadge.awarded_at.desc())
        .limit(20)
    )
    return [
        {
            "user_id": str(u.id),
            "user_name": f"{u.first_name} {u.last_name or ''}".strip(),
            "user_avatar": u.avatar_url,
            "badge_name": badge.name,
            "badge_description": badge.description,
            "badge_emoji": badge.emoji,
            "awarded_at": str(ub.awarded_at) if ub.awarded_at else None,
        }
        for ub, badge, u in result.all()
    ]


# --- My Badges ---

@badges_router.get("/My")
async def my_badges(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    result = await db.execute(
        select(UserBadge, Badge)
        .join(Badge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user.id)
    )
    return [
        {
            "id": str(badge.id),
            "name": badge.name,
            "description": badge.description,
            "emoji": badge.emoji,
            "icon_url": badge.icon_url,
            "awarded_at": str(ub.awarded_at) if ub.awarded_at else None,
        }
        for ub, badge in result.all()
    ]


# --- Award / Revoke ---

@badges_router.post("/Award")
async def award_badge(
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    user_id = uuid.UUID(data["user_id"])
    badge_id = uuid.UUID(data["badge_id"])
    result = await BadgeService(db).AwardBadge(user_id, str(badge_id))
    return {"message": result}


@badges_router.post("/Revoke")
async def revoke_badge(
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    user_id = uuid.UUID(data["user_id"])
    badge_id = uuid.UUID(data["badge_id"])
    result = await BadgeService(db).RevokeBadge(user_id, str(badge_id))
    return {"message": result}


# --- Set active badge ---

@badges_router.post("/SetActive")
async def set_active_badge(
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    badge_id = data.get("badge_id")

    if not badge_id:
        # Clear active badge
        user.active_badge_emoji = None
        await db.commit()
        return {"active_badge_emoji": None}

    badge = await db.get(Badge, uuid.UUID(badge_id))
    if not badge:
        raise HTTPException(status_code=404, detail="badge_not_found")

    # Check user has this badge
    existing = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user.id,
            UserBadge.badge_id == badge.id,
        )
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="badge_not_awarded")

    user.active_badge_emoji = badge.emoji
    await db.commit()
    return {"active_badge_emoji": user.active_badge_emoji}
