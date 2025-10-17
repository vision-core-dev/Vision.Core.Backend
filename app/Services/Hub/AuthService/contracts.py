import enum
import uuid
from datetime import datetime
from typing import Dict, Optional, List

from pydantic import BaseModel

from app.Objects.UserModel import MeUserBase
from app.Objects.UserRoleModel import MyUserRoleBase


class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    ok: bool
    token: str | uuid.UUID

class RegisterUserResponse(BaseModel):
    ok: bool
    user_id: uuid.UUID
    email: str
    password: str

class CheckMeResponse(BaseModel):
    ok: bool
    user: MeUserBase
    role: MyUserRoleBase