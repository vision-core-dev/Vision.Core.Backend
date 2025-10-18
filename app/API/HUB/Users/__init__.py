import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.UserService import UserService
from app.Services.Hub.UserService.contracts import CreateUserResponse, UsersListResponse, UserDetailsResponse, \
    CreateUserRequest

users_router = APIRouter(prefix="/Users", tags=["Hub > Users"])


# 📜 Отримати всіх користувачів
@users_router.get("/List", response_model=UsersListResponse)
async def list_users(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetUsersList()


# ➕ Створити користувача
@users_router.post("/Create", response_model=CreateUserResponse)
async def create_user(
    data: CreateUserRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await UserService(db).CreateUser(data.email, data.password, data.first_name)


# 👤 Деталі користувача
@users_router.get("/{user_id}/Details", response_model=UserDetailsResponse)
async def get_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetUserDetails(user_id, user)


@users_router.post("/{user_id}/Deactivate")
async def delete_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).DeactivateUser(user_id, user)

@users_router.post("/{user_id}/Activate")
async def delete_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).ActivateUser(user_id, user)

@users_router.post("/{user_id}/ChangeRole/{new_role_id}")
async def change_user_role(user_id: uuid.UUID, new_role_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).ChangeUserRole(user_id, new_role_id, user)

@users_router.post("/{user_id}/Supervisors/Add/{supervisor_id}")
async def add_supervisor(user_id: uuid.UUID, supervisor_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).AddSupervisor(user_id, supervisor_id, user)

@users_router.post("/{user_id}/Supervisors/Remove/{supervisor_id}")
async def remove_supervisor(user_id: uuid.UUID, supervisor_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).RemoveSupervisor(user_id, supervisor_id, user)

@users_router.post("/{user_id}/Subordinates/Add/{subordinate_id}")
async def add_subordinate(user_id: uuid.UUID, subordinate_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).AddSubordinate(user_id, subordinate_id, user)

@users_router.post("/{user_id}/Subordinates/Remove/{subordinate_id}")
async def remove_subordinate(user_id: uuid.UUID, subordinate_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).RemoveSubordinate(user_id, subordinate_id, user)
