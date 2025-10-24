from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService import AuthService, CheckMeResponse, LoginResponse
from app.Services.Hub.AuthService.contracts import LoginRequest
from app.Services.Hub.AuthService.depends import getuser, get_token, _get_user_by_token

auth_router = APIRouter(prefix="/Auth", tags=["Hub > Auth"])

@auth_router.post("/Login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(getdb)):
    return await AuthService(db).Login(data.email, data.password)

@auth_router.get("/CheckMe", response_model=CheckMeResponse, dependencies=[Depends(HTTPBearer(auto_error=False))])
async def me(
    user: User = Depends(lambda db=Depends(getdb), token=Depends(get_token): _get_user_by_token(db, token, is_check_me=True)),
    db: AsyncSession = Depends(getdb)
):
    return await AuthService(db).CheckMe(user)


@auth_router.post("/AcceptOffer")
async def accept_offer(
    user: User = Depends(lambda db=Depends(getdb), token=Depends(get_token): _get_user_by_token(db, token, is_accepting_terms=True)),
    db: AsyncSession = Depends(getdb)
):
    return await AuthService(db).AcceptOffer(user)
