from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService import AuthService
from app.Services.Hub.AuthService.contracts import OAuthCodeRequest, TelegramAuthRequest
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.AuthService.oauth import (
    get_google_user, get_discord_user, verify_telegram_auth, get_roblox_user,
)

linked_accounts_router = APIRouter(prefix="/LinkedAccounts", tags=["Hub > UserMe > LinkedAccounts"])


@linked_accounts_router.get("/Get")
async def get_linked_accounts(user: User = Depends(getuser)):
    return {
        "google": {"id": user.google_id, "username": user.google_email} if user.google_id else None,
        "discord": {"id": user.discord_id, "username": user.discord_username} if user.discord_id else None,
        "telegram": {"id": user.telegram_id, "username": user.telegram_username} if user.telegram_id else None,
        "roblox": {"id": user.roblox_id, "username": user.roblox_username} if user.roblox_id else None,
    }


# --- Link ---

@linked_accounts_router.post("/Link/Google")
async def link_google(data: OAuthCodeRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    try:
        info = await get_google_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="google_auth_failed")
    return await AuthService(db).LinkOAuth(user, info)


@linked_accounts_router.post("/Link/Discord")
async def link_discord(data: OAuthCodeRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    try:
        info = await get_discord_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="discord_auth_failed")
    return await AuthService(db).LinkOAuth(user, info)


@linked_accounts_router.post("/Link/Telegram")
async def link_telegram(data: TelegramAuthRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    try:
        info = verify_telegram_auth(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await AuthService(db).LinkOAuth(user, info)


@linked_accounts_router.post("/Link/Roblox")
async def link_roblox(data: OAuthCodeRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    try:
        info = await get_roblox_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="roblox_auth_failed")
    return await AuthService(db).LinkOAuth(user, info)


# --- Unlink ---

@linked_accounts_router.post("/Unlink/{provider}")
async def unlink_provider(provider: str, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await AuthService(db).UnlinkOAuth(user, provider)
