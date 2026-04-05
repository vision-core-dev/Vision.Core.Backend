import enum
import uuid
from datetime import datetime
from typing import Dict, Optional, List

from pydantic import BaseModel

from app.Objects.UserModel import MeUserBase, MyUserRoleBase


class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str | uuid.UUID

class RegisterUserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    password: str

class OAuthCodeRequest(BaseModel):
    code: str
    redirect_uri: str

class TelegramAuthRequest(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class CheckMeResponse(BaseModel):
    user: MeUserBase
    role: MyUserRoleBase