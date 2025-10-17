import enum
import uuid
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class TemporaryLoginRequest(BaseModel):
    tags: Dict[uuid.UUID, int] | None = None

class TemporaryLoginResponse(BaseModel):
    id: uuid.UUID
    temp_token: uuid.UUID
    is_temporary: bool
    created_at: datetime
    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    character_id: uuid.UUID
    confirmed_tags: Dict[uuid.UUID, int] | None = None

class CredentialsLoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class LoginResponse(BaseModel):
    id: uuid.UUID
    temp_token: uuid.UUID
    is_temporary: bool
    created_at: datetime
    class Config:
        from_attributes = True

class CheckUsernameResponse(BaseModel):
    available: bool
    detail: Optional[str] = None

class CheckUsernameRequest(BaseModel):
    username: str

class CharacterInfo(BaseModel):
    id: uuid.UUID
    name: str
    icon: Optional[str] = None

class MeResponse(BaseModel):
    id: uuid.UUID
    username: Optional[str] = None
    email: Optional[str] = None
    temp_token: uuid.UUID
    is_temporary: bool

    character: Optional[CharacterInfo]
    avatar_url: Optional[str] = None
    birthday: Optional[datetime] = None
    age: Optional[int] = None

    xp: int
    level: int
    coins: int

    created_at: datetime
