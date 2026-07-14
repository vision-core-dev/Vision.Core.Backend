import uuid

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser, require_role
from app.Objects.UserModel import UserRole
from app.Services.Hub.UserService import UserService
from app.Services.Hub.UserService.contracts import CreateUserResponse, UsersListResponse, UsersPublicListResponse, UserDetailsResponse, \
    CreateUserRequest, ChangeUserPasswordRequest

users_router = APIRouter(prefix="/Users", tags=["Hub > Users"])


# 📜 Отримати всіх користувачів
@users_router.get("/List", response_model=UsersListResponse)
async def list_users(only_active: bool = False, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetUsersList(only_active=only_active)


# 📜 Публічний список користувачів (тільки id, ім'я, аватар)
@users_router.get("/PublicList", response_model=UsersPublicListResponse)
async def list_users_public(db: AsyncSession = Depends(getdb)):
    return await UserService(db).GetPublicUsersList()


# ➕ Створити користувача
@users_router.post("/Create", response_model=CreateUserResponse)
async def create_user(
    data: CreateUserRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    # Only the user-management tier may create accounts.
    require_role(user, 2)

    # Prevent privilege escalation: the requested role must be strictly less
    # privileged than the actor's own role (higher order = lower privilege).
    if data.role_id is not None:
        new_role = await db.get(UserRole, data.role_id)
        if not new_role:
            raise HTTPException(status_code=404, detail="role_not_found")
        if user.role is None or new_role.order <= user.role.order:
            raise HTTPException(status_code=403, detail="insufficient_permissions")

    return await UserService(db).CreateUser(data.email, data.password, data.first_name, data.role_id)


# 👤 Деталі користувача
@users_router.get("/{user_id}/Details", response_model=UserDetailsResponse)
async def get_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    # Own details are always allowed; viewing others requires a manager+ role.
    if user.id != user_id:
        require_role(user, 3)
    return await UserService(db).GetUserDetails(user_id, user)


@users_router.post("/{user_id}/Deactivate")
async def delete_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).DeactivateUser(user_id, user)

@users_router.post("/{user_id}/Activate")
async def delete_user(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await UserService(db).ActivateUser(user_id, user)

@users_router.post("/{user_id}/ChangePassword", dependencies=[Depends(HTTPBearer(auto_error=False))])
async def reset_user_password(user_id: uuid.UUID, data: ChangeUserPasswordRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    if not data.new_password:
        raise HTTPException(status_code=400, detail="no_new_password")
    return await UserService(db).ChangeUserPassword(user_id, data.new_password, user, data.current_password)

@users_router.post("/{user_id}/ResetPassword", dependencies=[Depends(HTTPBearer(auto_error=False))])
async def admin_reset_password(user_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    import secrets
    from app.Services.Hub.AuthService.utils import get_hashed_password

    if not user.role or user.role.order > 2:
        raise HTTPException(status_code=403, detail="forbidden")

    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="user_not_found")

    new_password = secrets.token_urlsafe(10)
    target.hashed_password = get_hashed_password(new_password)
    await db.commit()

    return {"new_password": new_password}


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
