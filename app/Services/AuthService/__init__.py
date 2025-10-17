import os
import re
import uuid
from typing import Optional, Dict

from dotenv import load_dotenv
from fastapi import Request, HTTPException
from keyring.backends.libsecret import available

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.clans.ClanModel import Clan
from app.Objects.users.UserModel import User
from app.Objects.users.UserTagModel import UserTag
from app.Objects.content.tags.ContentTagModel import ContentTag
from app.Objects.content.tags.ContentTagGroupModel import ContentTagGroup
from app.Services.AnalyticService import AnalyticService
from app.Services.AuthService.contracts import TemporaryLoginResponse, TemporaryLoginRequest, LoginResponse, \
    CheckUsernameResponse
from app.Services.AuthService.google_auth import oauth
from app.Services.AuthService.utils import get_hashed_password, check_password


load_dotenv()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def Login(self, email: str, password: str) -> LoginResponse:
        if username and email:
            raise HTTPException(status_code=400, detail="provide_only_username_or_email")

        exist_user = None
        if not username is None:
            exist_user = await self.db.execute(select(User).where(User.username == username))
        elif not email is None:
            if "@" not in email:
                raise HTTPException(status_code=400, detail="invalid_email_format")
            exist_user = await self.db.execute(select(User).where(User.email == email))

        user = exist_user.scalar_one_or_none() if exist_user else None

        if not user:
            raise HTTPException(status_code=400, detail="user_not_found")

        if not user.hashed_password or not check_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="invalid_password")

        return LoginResponse.from_orm(user)

    async def CredentialsRegister(
            self,
            username: str,
            email: str,
            password: str,
            character_id: uuid.UUID,
            confirmed_tags: Optional[Dict[uuid.UUID, int]] = None,
            user: User = None
    ) -> LoginResponse:
        if "@" not in email:
            raise HTTPException(status_code=400, detail="invalid_email_format")

        await self.CheckUsername(username, raise_exception=True)

        exist_with_email = await self.db.execute(select(User).where(User.email == email))
        if exist_with_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="email_already_used")

        if len(password) < 8:
            raise HTTPException(status_code=400, detail="password_too_short")

        character_tag = await self.db.execute(
            select(ContentTag)
            .join(ContentTagGroup, ContentTag.group_id == ContentTagGroup.id)
            .where(
                ContentTag.id == character_id,
                ContentTagGroup.key == "characters"
            )
        )
        character_tag = character_tag.scalar_one_or_none()

        if not character_tag:
            raise HTTPException(
                status_code=400,
                detail="invalid_character_selection"
            )

        if user:
            if not user.is_temporary or user.email or user.username:
                raise HTTPException(status_code=400, detail="user_already_registered")

            # Оновлюємо тимчасового користувача
            user.email = email
            user.username = username
            user.hashed_password = get_hashed_password(password)
            user.character = character_id
            user.is_temporary = False
            # user.temp_token = uuid.uuid4()  # оновлюємо токен
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            new_user = user
        else:
            # Створюємо користувача
            new_user = User(
                email=email,
                username=username,
                hashed_password=get_hashed_password(password),
                character=character_id,
                temp_token=uuid.uuid4(),
            )
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

        # Теги
        if confirmed_tags:
            # Отримуємо всі наявні теги користувача за один запит
            existing_tags = await self.db.execute(
                select(UserTag).where(UserTag.user_id == new_user.id)
            )
            existing_tags = {tag.tag_id: tag for tag in existing_tags.scalars().all()}

            for tag_id, weight in confirmed_tags.items():
                if tag_id in existing_tags:
                    # Оновлюємо вагу, якщо тег уже існує
                    existing_tags[tag_id].weight = weight
                else:
                    # Створюємо новий тег
                    user_tag = UserTag(
                        user_id=new_user.id,
                        tag_id=tag_id,
                        weight=weight,
                    )
                    self.db.add(user_tag)

            await self.db.commit()

        # 🧠 Визначення клану на основі тегів
        if confirmed_tags:
            from app.Services.ClanService import ClanService  # імпортуємо тут, щоб уникнути циклічного імпорту
            clan_service = ClanService(self.db)
            best_clan_key = await clan_service.DetermineClan(confirmed_tags)

            if best_clan_key:
                # знаходимо клан по key
                clan_result = await self.db.execute(
                    select(Clan).where(Clan.key == best_clan_key)
                )
                clan = clan_result.scalar_one_or_none()
                if clan:
                    # додаємо користувача в клан
                    await clan_service.AddMember(clan.id, new_user.id)

        return LoginResponse.from_orm(new_user)

    async def Logout(self):
        pass

    async def TemporaryLogin(self, request: Request, tags: dict[uuid.UUID, int] | None = None) -> LoginResponse:
        user_agent = request.headers.get("User-Agent", "unknown")
        ip = request.headers.get("srcIp") or request.client.host

        device_info = {
            "platform": request.headers.get("Sec-CH-UA-Platform", "unknown"),
            "mobile": request.headers.get("Sec-CH-UA-Mobile", "unknown"),
        }

        temp_token = uuid.uuid4()

        region_code = await AnalyticService.GetGeoInfo(ip)

        existing = await self.db.execute(
            select(User).filter(
                User.is_temporary == True,
                User.user_agent == user_agent,
                User.ip_address == ip
            )
        )
        existing_user = existing.scalar_one_or_none()
        if existing_user:
            return TemporaryLoginResponse.from_orm(existing_user)

        temp_user = User(
            is_temporary=True,
            user_agent=user_agent,
            ip_address=ip,
            device_info=device_info or {},
            temp_token=temp_token,
            region_code=region_code,
        )

        self.db.add(temp_user)
        await self.db.commit()
        await self.db.refresh(temp_user)

        if tags:
            for tag_id, weight in tags.items():
                user_tag = UserTag(
                    user_id=temp_user.id,
                    tag_id=tag_id,
                    weight=weight,
                )
                self.db.add(user_tag)
            await self.db.commit()

        return LoginResponse.from_orm(temp_user)

    async def CheckUsername(self, username: str, raise_exception: bool = False) -> CheckUsernameResponse:
        if not re.match(r"^[A-Za-z0-9_]+$", username):
            if raise_exception:
                raise HTTPException(status_code=400, detail="invalid_username_format")
            return CheckUsernameResponse(available=False, detail="invalid_username_format")

        username = " ".join(username.strip().split())

        if len(username) < 3 or len(username) > 30:
            if raise_exception:
                raise HTTPException(status_code=400, detail="username_length_invalid")
            return CheckUsernameResponse(available=False, detail="username_length_invalid")

        exist_with_username = await self.db.execute(select(User).where(User.username == username))
        if exist_with_username.scalar_one_or_none():
            if raise_exception:
                raise HTTPException(status_code=400, detail="username_already_used")
            return CheckUsernameResponse(available=False, detail="username_already_used")

        return CheckUsernameResponse(available=True)