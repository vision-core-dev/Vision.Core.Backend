import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.DeveloperModel import Developer, DeveloperType
from app.Objects.DeveloperSchemas import (
    CreateDeveloperRequest,
    UpdateDeveloperRequest,
    DeveloperResponse,
    ListDevelopersResponse,
)
from app.Services.Hub.AuthService.depends import getuser, require_role

developers_router = APIRouter(prefix="/Developers", tags=["RoVision", "Developers"])


def check_permission(user: User):
    # Content management is restricted to managers and above (order <= 3).
    require_role(user, 3)


def _validate_type(value: str | None) -> None:
    if value is None:
        return
    allowed = {t.value for t in DeveloperType}
    if value not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type — must be one of {sorted(allowed)}",
        )


# ---------- Public ----------

@developers_router.get("/List", response_model=ListDevelopersResponse)
async def list_developers(db: AsyncSession = Depends(getdb)):
    stmt = (
        select(Developer)
        .where(Developer.is_published.is_(True))
        .order_by(asc(Developer.sort_order), asc(Developer.name))
    )
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@developers_router.get("/BySlug/{slug}", response_model=DeveloperResponse)
async def get_developer_by_slug(slug: str, db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(Developer).where(Developer.slug == slug))
    dev = result.scalar_one_or_none()
    if not dev or not dev.is_published:
        raise HTTPException(status_code=404, detail="Developer not found")
    return dev


# ---------- Admin ----------

@developers_router.get("/Admin/List", response_model=ListDevelopersResponse)
async def admin_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    stmt = select(Developer).order_by(asc(Developer.sort_order), asc(Developer.name))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@developers_router.get("/Admin/{developer_id}", response_model=DeveloperResponse)
async def admin_get(
    developer_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return dev


@developers_router.post("/Create", response_model=DeveloperResponse)
async def create_developer(
    data: CreateDeveloperRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    _validate_type(data.type)

    payload = data.model_dump()
    payload["socials"] = [s if isinstance(s, dict) else s.model_dump() for s in payload.get("socials", [])]

    dev = Developer(**payload)
    db.add(dev)
    try:
        await db.commit()
        await db.refresh(dev)
        return dev
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Slug already exists")


@developers_router.patch("/{developer_id}/Update", response_model=DeveloperResponse)
async def update_developer(
    developer_id: uuid.UUID,
    data: UpdateDeveloperRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    updates = data.model_dump(exclude_unset=True)
    if "type" in updates:
        _validate_type(updates["type"])
    if "socials" in updates and updates["socials"] is not None:
        updates["socials"] = [
            s if isinstance(s, dict) else s.model_dump() for s in updates["socials"]
        ]
    for k, v in updates.items():
        setattr(dev, k, v)

    try:
        await db.commit()
        await db.refresh(dev)
        return dev
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Slug already exists")


@developers_router.delete("/{developer_id}/Delete")
async def delete_developer(
    developer_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    dev = await db.get(Developer, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    await db.delete(dev)
    await db.commit()
    return {"status": "ok"}
