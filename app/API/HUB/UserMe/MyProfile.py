import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, UploadFile, Depends, HTTPException
from fastapi.params import File
from pydantic import BaseModel
from starlette import status

from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Infrastructure.Database import getdb
from sqlalchemy.ext.asyncio import AsyncSession

my_profile_router = APIRouter()


class SetBirthdayRequest(BaseModel):
    birthday: date

@my_profile_router.post("/SetBirthday", status_code=200)
async def set_birthday(
    data: SetBirthdayRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    # 🕒 date -> datetime (UTC)
    birthday_dt = datetime.combine(
        data.birthday,
        time.min,
        tzinfo=timezone.utc
    )

    user.birthday = birthday_dt

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "status": "ok",
        "birthday": user.birthday.isoformat()
    }




ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


@my_profile_router.post("/UploadAvatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    # 🔒 type validation
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type",
        )

    contents = await file.read()

    # 🔒 size validation
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large (max 5MB)",
        )

    filename = f"avatars/{user.id}_{uuid.uuid4()}.{file.filename.split('.')[-1]}"

    # ☁️ upload to Bunny
    file_url = await _upload_to_bunny(
        filename,
        contents,
        file.content_type,
    )

    # 💾 save to DB
    user.avatar_url = file_url
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "avatar_url": file_url,
    }


class ChangeMyPasswordRequest(BaseModel):
    current_password: str
    new_password: str


@my_profile_router.post("/ChangePassword", status_code=200)
async def change_my_password(
    data: ChangeMyPasswordRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    from app.Services.Hub.AuthService.utils import check_password, get_hashed_password

    if not user.hashed_password or not check_password(data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="invalid_current_password")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="password_too_short")

    user.hashed_password = get_hashed_password(data.new_password)
    db.add(user)
    await db.commit()

    return {"status": "ok"}


class UpdateNotifySettingsRequest(BaseModel):
    notify_discord: bool | None = None
    notify_telegram: bool | None = None


@my_profile_router.post("/UpdateNotifySettings", status_code=200)
async def update_notify_settings(
    data: UpdateNotifySettingsRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    if data.notify_discord is not None:
        if data.notify_discord and not user.discord_id:
            raise HTTPException(status_code=400, detail="discord_not_linked")
        user.notify_discord = data.notify_discord

    if data.notify_telegram is not None:
        if data.notify_telegram and not user.telegram_id:
            raise HTTPException(status_code=400, detail="telegram_not_linked")
        user.notify_telegram = data.notify_telegram

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "notify_discord": user.notify_discord,
        "notify_telegram": user.notify_telegram,
    }