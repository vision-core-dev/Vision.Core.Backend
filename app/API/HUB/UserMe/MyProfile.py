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