from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.Objects.BadgeModel import UserBadgeBase
from app.Objects.UserModel import UserBase, UserPreview, UserShort
from app.Objects.finance.TransactionModel import TransactionBase


class UsersListResponse(BaseModel):
    total: int
    list: List[UserPreview]

    class Config:
        from_attributes = True


class UsersPublicListResponse(BaseModel):
    total: int
    list: List[UserShort]

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    password: str
    role_id: Optional[UUID] = None


class CreateUserResponse(BaseModel):
    user_id: UUID


class UserTaskPreview(BaseModel):
    id: UUID
    name: str
    status: str
    deadline_at: Optional[datetime] = None
    board_id: UUID
    list_name: Optional[str] = None


class UserPositionPreview(BaseModel):
    position: str = ""
    project: Optional[str] = None
    project_type: Optional[str] = None
    is_head: bool = False


class UserDetailsResponse(BaseModel):
    user: UserBase
    actions: list[str] = []
    supervisors: list[UserPreview] = []
    subordinates: list[UserPreview] = []
    badges: list[UserBadgeBase] = []
    transactions: list[TransactionBase] = []
    tasks: list[UserTaskPreview] = []
    positions: list[UserPositionPreview] = []
    tasks_total_completed: int = 0
    tasks_total_active: int = 0

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

class ChangeUserPasswordRequest(BaseModel):
    new_password: str
    # Required when a user changes their OWN password (verifies identity).
    current_password: Optional[str] = None