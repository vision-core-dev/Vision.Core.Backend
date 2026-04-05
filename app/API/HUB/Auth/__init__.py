from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService import AuthService, CheckMeResponse, LoginResponse
from app.Services.Hub.AuthService.contracts import LoginRequest, OAuthCodeRequest, TelegramAuthRequest
from app.Services.Hub.AuthService.depends import getuser_check_me, \
    getuser_accepting_terms
from app.Services.Hub.AuthService.oauth import (
    get_google_user, get_discord_user, verify_telegram_auth, get_roblox_user,
)

auth_router = APIRouter(prefix="/Auth", tags=["Hub > Auth"])

@auth_router.post("/Login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(getdb)):
    return await AuthService(db).Login(data.email, data.password)


@auth_router.get("/CheckMe", response_model=CheckMeResponse, dependencies=[Depends(HTTPBearer(auto_error=False))])
async def me(user: User = Depends(getuser_check_me), db: AsyncSession = Depends(getdb)):
    return await AuthService(db).CheckMe(user)


@auth_router.post("/AcceptOffer")
async def accept_offer(user: User = Depends(getuser_accepting_terms), db: AsyncSession = Depends(getdb)):
    return await AuthService(db).AcceptOffer(user)


# --- OAuth Login ---

@auth_router.post("/Login/Google", response_model=LoginResponse)
async def login_google(data: OAuthCodeRequest, db: AsyncSession = Depends(getdb)):
    try:
        info = await get_google_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="google_auth_failed")
    return await AuthService(db).OAuthLogin(info)


@auth_router.post("/Login/Discord", response_model=LoginResponse)
async def login_discord(data: OAuthCodeRequest, db: AsyncSession = Depends(getdb)):
    try:
        info = await get_discord_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="discord_auth_failed")
    return await AuthService(db).OAuthLogin(info)


@auth_router.post("/Login/Telegram", response_model=LoginResponse)
async def login_telegram(data: TelegramAuthRequest, db: AsyncSession = Depends(getdb)):
    try:
        info = verify_telegram_auth(data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await AuthService(db).OAuthLogin(info)


@auth_router.post("/Login/Roblox", response_model=LoginResponse)
async def login_roblox(data: OAuthCodeRequest, db: AsyncSession = Depends(getdb)):
    try:
        info = await get_roblox_user(data.code, data.redirect_uri)
    except Exception:
        raise HTTPException(status_code=400, detail="roblox_auth_failed")
    return await AuthService(db).OAuthLogin(info)