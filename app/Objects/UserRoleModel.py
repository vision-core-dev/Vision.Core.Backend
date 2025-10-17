import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import func, UUID, Column, String, ARRAY, TEXT, DateTime

from app.Infrastructure.Database import Base


class UserRole(Base):
    __tablename__ = "UserRoles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False)

    menu = Column(ARRAY(TEXT), nullable=False, default=[])
    # ["dashboard", "profile", "settings"]

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

class SmallUserRoleBase(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    class Config:
        from_attributes = True

class UserRoleBase(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    menu: list[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MyUserRoleBase(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    menu: list[str]
    class Config:
        from_attributes = True