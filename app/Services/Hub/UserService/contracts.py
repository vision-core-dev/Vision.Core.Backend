from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.Objects.UserModel import SmallUserBase, UserBase


class UsersListResponse(BaseModel):
    total: int
    list: List[SmallUserBase]

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    password: str


class CreateUserResponse(BaseModel):
    user_id: UUID


class UserDetailsResponse(BaseModel):
    user: UserBase
    actions: list[str] = []
    supervisors: list[SmallUserBase] = []
    subordinates: list[SmallUserBase] = []

    class Config:
        from_attributes = True


class ActivateUserResponse(BaseModel):
    user_id: UUID


class DeactivateUserResponse(BaseModel):
    user_id: UUID


class DetailsUserResponse(BaseModel):
    user: UserBase
    actions: Optional[List[str]] = None

    class Config:
        from_attributes = True