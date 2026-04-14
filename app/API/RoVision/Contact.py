import asyncio
import os
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.ContactRequestModel import ContactRequest
from app.Objects.ContactRequestSchemas import (
    CreateContactRequest,
    ContactRequestResponse,
    ListContactRequestsResponse,
    UpdateContactRequest,
)
from app.Services.Hub.AuthService.depends import getuser

contact_router = APIRouter(prefix="/Contact", tags=["RoVision > Contact"])

CONTACT_WEBHOOK_URL = os.getenv("CONTACT_WEBHOOK_URL")
CONTACT_WEBHOOK_TOKEN = os.getenv("CONTACT_WEBHOOK_TOKEN")

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def _verify_turnstile(token: str | None, remote_ip: str | None) -> bool:
    if not TURNSTILE_SECRET_KEY:
        return True  # turnstile not configured — skip
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            data = {"secret": TURNSTILE_SECRET_KEY, "response": token}
            if remote_ip:
                data["remoteip"] = remote_ip
            r = await client.post(TURNSTILE_VERIFY_URL, data=data)
            result = r.json()
            return bool(result.get("success"))
    except Exception as e:
        print(f"[Turnstile] verify failed: {e}")
        return False


async def _send_webhook(payload: dict) -> None:
    if not CONTACT_WEBHOOK_URL:
        return
    headers = {"Content-Type": "application/json"}
    if CONTACT_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {CONTACT_WEBHOOK_TOKEN}"
        headers["X-Webhook-Token"] = CONTACT_WEBHOOK_TOKEN
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(CONTACT_WEBHOOK_URL, json=payload, headers=headers)
    except Exception as e:
        print(f"[Contact webhook] failed: {e}")


def check_permission(user: User):
    if not user.role or user.role.order not in [0, 1, 2, 3, 4, 5, 6]:
        raise HTTPException(status_code=403, detail="Тільки авторизовані користувачі можуть переглядати звернення")


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------- Public ----------

@contact_router.post("/Create", response_model=ContactRequestResponse)
async def create_request(
    data: CreateContactRequest,
    request: Request,
    db: AsyncSession = Depends(getdb),
):
    client_ip = _client_ip(request)

    if not await _verify_turnstile(data.turnstile_token, client_ip):
        raise HTTPException(status_code=403, detail="Не вдалося пройти перевірку Cloudflare. Оновіть сторінку та спробуйте ще раз.")

    telegram = data.telegram
    if telegram:
        telegram = telegram.strip().lstrip("@")
        telegram = f"@{telegram}" if telegram else None

    entry = ContactRequest(
        category=data.category,
        category_label=data.category_label,
        email=str(data.email) if data.email else None,
        phone=data.phone.strip() if data.phone else None,
        telegram=telegram,
        message=data.message.strip(),
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    asyncio.create_task(_send_webhook({
        "id": str(entry.id),
        "category": entry.category,
        "category_label": entry.category_label,
        "email": entry.email,
        "phone": entry.phone,
        "telegram": entry.telegram,
        "message": entry.message,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }))

    return entry


# ---------- Admin ----------

@contact_router.get("/Admin/List", response_model=ListContactRequestsResponse)
async def list_requests(
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
    only_unhandled: bool = False,
):
    check_permission(user)
    stmt = select(ContactRequest).order_by(desc(ContactRequest.created_at))
    if only_unhandled:
        stmt = stmt.where(ContactRequest.is_handled.is_(False))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@contact_router.patch("/{request_id}/Update", response_model=ContactRequestResponse)
async def update_request(
    request_id: uuid.UUID,
    data: UpdateContactRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    entry = await db.get(ContactRequest, request_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Request not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)

    await db.commit()
    await db.refresh(entry)
    return entry


@contact_router.delete("/{request_id}/Delete")
async def delete_request(
    request_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)
    entry = await db.get(ContactRequest, request_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Request not found")

    await db.delete(entry)
    await db.commit()
    return {"status": "success"}
