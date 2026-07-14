import uuid
from datetime import datetime

import httpx
import pytz
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.UserModel import User, MeUserBase, UserRole, MyUserRoleBase
from app.Services.Hub.AuthService.contracts import LoginResponse, CheckMeResponse, RegisterUserResponse
from app.Services.Hub.AuthService.oauth import OAuthUserInfo
from app.Services.Hub.AuthService.utils import get_hashed_password, check_password

PROVIDER_ID_FIELD = {
    "google": "google_id",
    "discord": "discord_id",
    "telegram": "telegram_id",
    "roblox": "roblox_id",
}

PROVIDER_USERNAME_FIELD = {
    "google": "google_email",
    "discord": "discord_username",
    "telegram": "telegram_username",
    "roblox": "roblox_username",
}


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

        # Guarantee a valid session token — a NULL temp_token would serialize to
        # the literal string "None" and break every authenticated request.
        if not user.temp_token:
            user.temp_token = uuid.uuid4()
            await self.db.commit()
            await self.db.refresh(user)

        return LoginResponse(token=str(user.temp_token))

    async def CheckMe(self, user: User) -> CheckMeResponse:
        if not user:
            raise HTTPException(status_code=400, detail="user_not_found")

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

    async def RegisterUser(self, email: str | EmailStr, password: str, first_name: str = "Name", role_id: uuid.UUID | None = None) -> RegisterUserResponse:
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

        final_role_id = role_id if role_id is not None else default_role.id

        new_user = User(
            email=email,
            hashed_password=get_hashed_password(password),
            is_active=True,
            first_name=first_name,
            role_id=final_role_id,
            supervisor_ids=[],
            temp_token=uuid.uuid4(),
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return RegisterUserResponse(user_id=new_user.id, email=email, password=password)

    async def _sync_avatar_from_oauth(self, user: User, info: OAuthUserInfo) -> None:
        if user.avatar_url or not info.avatar_url:
            return
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(info.avatar_url)
                if res.status_code != 200:
                    return
                content_type = res.headers.get("content-type", "image/png")
                ext = "png" if "png" in content_type else "jpg"
                path = f"avatars/{user.id}_{uuid.uuid4()}.{ext}"
                file_url = await _upload_to_bunny(path, res.content, content_type)
                user.avatar_url = file_url
        except Exception:
            pass

    async def OAuthLogin(self, info: OAuthUserInfo) -> LoginResponse:
        id_field = PROVIDER_ID_FIELD[info.provider]

        result = await self.db.execute(
            select(User).where(getattr(User, id_field) == info.provider_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=400, detail="oauth_account_not_linked")

        if not user.is_active:
            raise HTTPException(status_code=400, detail="user_is_deactivated")

        if not user.role_id:
            default_role_result = await self.db.execute(
                select(UserRole).where(UserRole.key == "default")
            )
            default_role = default_role_result.scalar_one_or_none()
            if not default_role:
                raise HTTPException(status_code=500, detail="default_role_not_found")
            user.role_id = str(default_role.id)

        await self._sync_avatar_from_oauth(user, info)

        # Guarantee a valid session token (see Login) — never return "None".
        if not user.temp_token:
            user.temp_token = uuid.uuid4()

        user.last_login = func.now()
        await self.db.commit()
        await self.db.refresh(user)

        return LoginResponse(token=str(user.temp_token))

    async def LinkOAuth(self, user: User, info: OAuthUserInfo) -> dict:
        id_field = PROVIDER_ID_FIELD[info.provider]
        username_field = PROVIDER_USERNAME_FIELD[info.provider]

        existing = await self.db.execute(
            select(User).where(getattr(User, id_field) == info.provider_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="oauth_account_already_used")

        setattr(user, id_field, info.provider_id)
        setattr(user, username_field, info.username or info.email)

        await self._sync_avatar_from_oauth(user, info)

        await self.db.commit()
        await self.db.refresh(user)

        return {
            "provider": info.provider,
            "provider_id": info.provider_id,
            "username": info.username or info.email,
        }

    async def UnlinkOAuth(self, user: User, provider: str) -> dict:
        if provider not in PROVIDER_ID_FIELD:
            raise HTTPException(status_code=400, detail="invalid_provider")

        id_field = PROVIDER_ID_FIELD[provider]
        username_field = PROVIDER_USERNAME_FIELD[provider]

        if not getattr(user, id_field):
            raise HTTPException(status_code=400, detail="provider_not_linked")

        setattr(user, id_field, None)
        setattr(user, username_field, None)

        await self.db.commit()
        await self.db.refresh(user)

        return {"provider": provider, "unlinked": True}

    async def AcceptOffer(self, user: User) -> None:
        if not user:
            raise HTTPException(status_code=400, detail="user_not_found")

        if not user.is_need_accept_terms:
            raise HTTPException(status_code=400, detail="terms_already_accepted")

        if user.is_terms_accepted:
            raise HTTPException(status_code=400, detail="terms_already_accepted")

        kyiv_tz = pytz.timezone("Europe/Kyiv")

        user.is_terms_accepted = True
        user.terms_accepted_at = datetime.now(kyiv_tz)

        await self.db.commit()
        await self.db.refresh(user)