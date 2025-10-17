import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.UserService import UserService
from app.Services.Hub.UserService.contracts import CreateUserResponse, UsersListResponse, UserDetailsResponse, \
    CreateUserRequest

users_router = APIRouter(prefix="/Users", tags=["Hub > Users"])


# 📜 Отримати всіх користувачів
@users_router.get("/List", response_model=UsersListResponse)
async def list_users(db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetUsersList()


# ➕ Створити користувача
@users_router.post("/Create", response_model=CreateUserResponse)
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(getdb)
):
    return await UserService(db).CreateUser(data.email, data.password, data.first_name)


# 👤 Деталі користувача
@users_router.get("/{user_id}/Details", response_model=UserDetailsResponse)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetUserDetails(user_id)


@users_router.post("/{user_id}/Deactivate")
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(getdb)):
    return await UserService(db).DeactivateUser(user_id)

@users_router.post("/{user_id}/Activate")
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(getdb)):
    return await UserService(db).ActivateUser(user_id)
