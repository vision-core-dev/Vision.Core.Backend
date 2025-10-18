import uuid
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, any_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.Objects.BadgeModel import UserBadge, Badge, UserBadgeBase
from app.Objects.UserModel import User
from app.Objects.UserRoleModel import UserRole
from app.Services.Hub.AuthService import AuthService
from app.Services.Hub.UserService.contracts import (
    UsersListResponse,
    UserDetailsResponse,
    CreateUserRequest,
    CreateUserResponse,
    ActivateUserResponse,
    DeactivateUserResponse
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def CreateUser(self, email: str | EmailStr, password: str, first_name: str) -> CreateUserResponse:
        result = await AuthService(self.db).RegisterUser(email, password, first_name)
        return CreateUserResponse(user_id=result.user_id)

    async def GetUsersList(self) -> UsersListResponse:
        stmt = await self.db.execute(
            select(User).options(selectinload(User.role))
        )
        result = stmt.scalars().all()
        return UsersListResponse(total=len(result), list=result)

    async def GetUserDetails(self, user_id: uuid.UUID, actor: User) -> UserDetailsResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)
        target_role = await self.db.get(UserRole, user.role_id)

        actions = []
        if actor_role.order < target_role.order:
            actions.append("change_role")
            if user.is_active:
                actions.append("deactivate_user")
            else:
                actions.append("activate_user")
        if actor_role.order <= 1:
            actions.append("give_badge")
            actions.append("remove_badge")

        # 🧑‍💼 Керівники
        supervisors = []
        if user.supervisor_ids:
            q = await self.db.execute(
                select(User).where(User.id.in_(user.supervisor_ids)).options(selectinload(User.role))
            )
            supervisors = q.scalars().all()

        # 👨‍💻 Підлеглі
        q2 = await self.db.execute(
            select(User)
            .where(user.id == any_(User.supervisor_ids))
            .options(selectinload(User.role))
        )
        subordinates = q2.scalars().all()

        # 🏅 Бейджі користувача (інтегровано тут)
        badge_stmt = (
            select(UserBadge)
            .where(UserBadge.user_id == user.id)
            .options(joinedload(UserBadge.badge))  # ✅ тепер це працює
        )

        badge_result = await self.db.execute(badge_stmt)
        user_badges = badge_result.scalars().all()

        badges = [
            UserBadgeBase(
                id=ub.badge.id,
                name=ub.badge.name,
                description=ub.badge.description,
                icon_url=ub.badge.icon_url,
                emoji=ub.badge.emoji,
                awarded_at=ub.awarded_at
            )
            for ub in user_badges
        ]

        return UserDetailsResponse(
            user=user,
            actions=actions,
            supervisors=supervisors,
            subordinates=subordinates,
            badges=badges  # 👈 нове поле
        )

    async def DeactivateUser(self, user_id: uuid.UUID) -> DeactivateUserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        user.is_active = False
        await self.db.commit()

        return DeactivateUserResponse(user_id=user.id)

    async def ActivateUser(self, user_id: uuid.UUID) -> ActivateUserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        user.is_active = True
        await self.db.commit()

        return ActivateUserResponse(user_id=user.id)
