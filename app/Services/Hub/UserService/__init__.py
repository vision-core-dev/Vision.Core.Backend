import uuid
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, any_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.Objects.UserModel import User
from app.Objects.UserRoleModel import UserRole
from app.Services.Hub.AuthService import AuthService
from app.Services.Hub.AuthService.utils import get_hashed_password
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
        return CreateUserResponse(ok=True, user_id=result.user_id)

    async def GetUsersList(self) -> UsersListResponse:
        stmt = await self.db.execute(
            select(User).options(selectinload(User.role))
        )
        result = stmt.scalars().all()
        return UsersListResponse(ok=True, total=len(result), users=result)

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

        # 🧑‍💼 Отримуємо керівників
        supervisors = []
        if user.supervisor_ids:
            q = await self.db.execute(
                select(User).where(User.id.in_(user.supervisor_ids)).options(selectinload(User.role))
            )
            supervisors = q.scalars().all()

        # 👨‍💻 Отримуємо підлеглих
        q2 = await self.db.execute(
            select(User)
            .where(user.id == any_(User.supervisor_ids))
            .options(selectinload(User.role))
        )
        subordinates = q2.scalars().all()

        return UserDetailsResponse(
            ok=True,
            user=user,
            actions=actions,
            supervisors=supervisors,
            subordinates=subordinates
        )

    async def DeactivateUser(self, user_id: uuid.UUID) -> DeactivateUserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        user.is_active = False
        await self.db.commit()

        return DeactivateUserResponse(ok=True, user_id=user.id)

    async def ActivateUser(self, user_id: uuid.UUID) -> ActivateUserResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        user.is_active = True
        await self.db.commit()

        return ActivateUserResponse(ok=True, user_id=user.id)
