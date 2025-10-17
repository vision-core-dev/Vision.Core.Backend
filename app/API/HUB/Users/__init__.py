from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService import LoginResponse, AuthService
from app.Services.Hub.AuthService.contracts import LoginRequest, RegisterUserResponse

users_router = APIRouter(prefix="/Users", tags=["Hub > Users"])

@users_router.post("/RegisterUser", response_model=RegisterUserResponse)
async def register_user(data: LoginRequest, db: AsyncSession = Depends(getdb)):
    return await AuthService(db).RegisterUser(data.email, data.password)