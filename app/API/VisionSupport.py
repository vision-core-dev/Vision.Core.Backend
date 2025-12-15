from typing import List

from fastapi import APIRouter, Depends, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Infrastructure.Storage import _upload_to_bunny
from app.Objects.UserModel import User
from app.Objects.VisionSupport import VisionSupportUser, VisionSupportAnswer, VisionSupportMessage
from app.Services.Hub.AuthService.depends import getuser

vision_support_router = APIRouter(prefix="/VisionSupport", tags=["Vision Support"])

class VisionSupportUserModel(BaseModel):
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    is_active: bool
    new_messages: int | None = 0

class GetBotUsersResponse(BaseModel):
    users: list[VisionSupportUserModel]

class GetMessagesRequest(BaseModel):
    telegram_user_id: int

class SendAnswerRequest(BaseModel):
    telegram_user_id: int
    text: str | None = None
    files: list[str] = []


@vision_support_router.get("/GetBotUsers", response_model=GetBotUsersResponse)
async def get_users(
    db: AsyncSession = Depends(getdb),
    _: User = Depends(getuser),
):
    stmt = (
        select(VisionSupportUser)
        .order_by(
            VisionSupportUser.new_messages.desc(),
            VisionSupportUser.created_at.desc()
        )
    )

    result = await db.execute(stmt)
    users = result.scalars().all()

    return GetBotUsersResponse(
        users=[
            VisionSupportUserModel(
                telegram_id=u.telegram_id,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                is_active=u.is_active,
                new_messages=u.new_messages or 0,
            )
            for u in users
        ]
    )



@vision_support_router.post("/GetMessages")
async def get_messages(
    data: GetMessagesRequest,
    db: AsyncSession = Depends(getdb),
    _: User = Depends(getuser),
):
    user = await db.get(VisionSupportUser, data.telegram_user_id)
    if not user:
        return {"items": []}

    # 🔹 ЯВНО тягнемо повідомлення
    messages_result = await db.execute(
        select(VisionSupportMessage)
        .where(VisionSupportMessage.telegram_user_id == data.telegram_user_id)
    )
    messages = messages_result.scalars().all()

    answers_result = await db.execute(
        select(VisionSupportAnswer)
        .where(VisionSupportAnswer.telegram_user_id == data.telegram_user_id)
    )
    answers = answers_result.scalars().all()

    items: list[dict] = []

    for m in messages:
        items.append({
            "id": str(m.id),
            "from": "user",
            "text": m.text,
            "files": m.files or [],
            "created_at": m.created_at,
        })

    for a in answers:
        items.append({
            "id": str(a.id),
            "from": "operator",
            "text": a.text,
            "files": a.files or [],
            "created_at": a.created_at,
        })

    items.sort(key=lambda x: x["created_at"])

    # 👁️ скидаємо лічильник
    user.new_messages = 0
    await db.commit()

    return {"items": items}


@vision_support_router.post("/SendAnswer")
async def send_answer(
    telegram_user_id: int = Form(...),
    text: str | None = Form(None),
    files: List[UploadFile] = File(default=[]),

    db: AsyncSession = Depends(getdb),
    operator: User = Depends(getuser),
):
    user = await db.get(VisionSupportUser, telegram_user_id)
    if not user:
        return {"ok": False, "error": "user_not_found"}

    uploaded_urls: list[str] = []

    for file in files:
        data = await file.read()
        path = f"support/{telegram_user_id}/{file.filename}"

        url = await _upload_to_bunny(
            path=path,
            data=data,
            content_type=file.content_type or "application/octet-stream"
        )
        uploaded_urls.append(url)

    answer = VisionSupportAnswer(
        telegram_user_id=telegram_user_id,
        operator_id=operator.id,
        text=text or "",
        files=uploaded_urls,
    )

    db.add(answer)
    await db.commit()

    return {"ok": True}