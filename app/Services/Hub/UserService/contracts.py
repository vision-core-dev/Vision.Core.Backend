from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.Objects.UserModel import SmallUserBase, UserBase


class UsersListResponse(BaseModel):
    ok: bool
    total: int
    users: List[SmallUserBase]

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    password: str


class CreateUserResponse(BaseModel):
    ok: bool
    user_id: UUID


class UserDetailsResponse(BaseModel):
    ok: bool
    user: UserBase

    class Config:
        from_attributes = True


class ActivateUserResponse(BaseModel):
    ok: bool
    user_id: UUID


class DeactivateUserResponse(BaseModel):
    ok: bool
    user_id: UUID


class DetailsUserResponse(BaseModel):
    ok: bool
    user: UserBase
    actions: Optional[List[str]] = None

    class Config:
        from_attributes = True