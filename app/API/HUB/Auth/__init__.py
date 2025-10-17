from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService import AuthService, CheckMeResponse, LoginResponse
from app.Services.Hub.AuthService.contracts import LoginRequest
from app.Services.Hub.AuthService.depends import getuser

auth_router = APIRouter(prefix="/Auth", tags=["Hub > Auth"])

@auth_router.post("/Login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(getdb)):
    return await AuthService(db).Login(data.email, data.password)

@auth_router.get("/CheckMe", response_model=CheckMeResponse, dependencies=[Depends(HTTPBearer(auto_error=False))])
async def me(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await AuthService(db).CheckMe(user)