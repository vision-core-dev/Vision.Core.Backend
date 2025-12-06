from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
import redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService import AuthService, CheckMeResponse, LoginResponse
from app.Services.Hub.AuthService.contracts import LoginRequest
from app.Services.Hub.AuthService.depends import getuser_check_me, \
    getuser_accepting_terms

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