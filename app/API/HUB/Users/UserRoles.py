from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User, UserRoleBase, UserRole, UserRoleCreate, UserRoleUpdate
from app.Services.Hub.AuthService.depends import getuser

user_roles_router = APIRouter(prefix="/UserRoles", tags=["Hub > UserRoles"])

@user_roles_router.get("/MyLowerRoles", response_model=list[UserRoleBase])
async def get_my_lower_roles(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    actor_role = await db.get(UserRole, user.role_id)
    if not actor_role:
        return []

    stmt = await db.execute(
        select(UserRole).where(actor_role.order < UserRole.order).order_by(UserRole.order.asc())
    )
    result = stmt.scalars().all()

    return result

@user_roles_router.get("", response_model=list[UserRoleBase])
async def get_all_roles(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    stmt = await db.execute(select(UserRole).order_by(UserRole.order.asc()))
    return stmt.scalars().all()

@user_roles_router.post("", response_model=UserRoleBase)
async def create_role(data: UserRoleCreate, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    new_role = UserRole(**data.model_dump())
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)
    return new_role

@user_roles_router.patch("/{role_id}", response_model=UserRoleBase)
async def update_role(role_id: uuid.UUID, data: UserRoleUpdate, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    role = await db.get(UserRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
        
    await db.commit()
    await db.refresh(role)
    return role

@user_roles_router.delete("/{role_id}")
async def delete_role(role_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    role = await db.get(UserRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    await db.delete(role)
    await db.commit()
    return {"status": "ok"}