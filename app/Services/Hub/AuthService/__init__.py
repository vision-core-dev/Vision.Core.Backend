import uuid

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.UserModel import User, MeUserBase, UserRole, MyUserRoleBase
from app.Services.Hub.AuthService.contracts import LoginResponse, CheckMeResponse, RegisterUserResponse
from app.Services.Hub.AuthService.utils import get_hashed_password, check_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def Login(self, email: str, password: str) -> LoginResponse:
        if not email or not password:
            raise HTTPException(status_code=400, detail="provide_username_or_email")

        exist_user = await self.db.execute(select(User).where(User.email == email))
        user = exist_user.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="user_not_found")

        if not user.hashed_password or not check_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="invalid_password")

        # 🔑 Якщо роль не задана — знайдемо роль із key="default" і призначимо її
        if not user.role_id:
            default_role_result = await self.db.execute(
                select(UserRole).where(UserRole.key == "default")
            )
            default_role = default_role_result.scalar_one_or_none()

            if not default_role:
                raise HTTPException(
                    status_code=500,
                    detail="default_role_not_found"
                )

            user.role_id = str(default_role.id)
            await self.db.commit()
            await self.db.refresh(user)

        return LoginResponse(token=str(user.temp_token))

    async def CheckMe(self, user: User) -> CheckMeResponse:
        if not user:
            raise HTTPException(status_code=400, detail="user_not_found")

        # 🔎 Отримуємо роль користувача
        role_result = await self.db.execute(
            select(UserRole).where(UserRole.id == user.role_id)
        )
        role = role_result.scalar_one_or_none()

        if not role:
            raise HTTPException(status_code=404, detail="role_not_found")

        user.last_login = func.now()
        await self.db.commit()
        await self.db.refresh(user)

        return CheckMeResponse(
            user=MeUserBase.from_orm(user),
            role=MyUserRoleBase.from_orm(role),
        )

    async def RegisterUser(self, email: str | EmailStr, password: str, first_name: str = "Name") -> RegisterUserResponse:
        if not email or not password:
            raise HTTPException(status_code=400, detail="provide_email_and_password")

        result = await self.db.execute(
            select(UserRole).where(UserRole.key == "default")
        )
        default_role = result.scalar_one_or_none()

        if not default_role:
            raise HTTPException(status_code=500, detail="default_role_not_found")

        exist_user = await self.db.execute(select(User).where(User.email == email))
        if exist_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="email_already_used")

        if len(password) < 8:
            raise HTTPException(status_code=400, detail="password_too_short")

        new_user = User(
            email=email,
            hashed_password=get_hashed_password(password),
            is_active=True,
            first_name=first_name,
            role_id=str(default_role.id),
            supervisor_ids=[],
            temp_token=uuid.uuid4(),
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return RegisterUserResponse(user_id=new_user.id, email=email, password=password)