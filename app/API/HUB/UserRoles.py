from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.UserRoleModel import UserRoleBase, UserRole
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

    print(actor_role.order, result)

    return result