import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, UUID, func, ARRAY, ForeignKey, Boolean, sql
from sqlalchemy.orm import relationship, backref

from app.Infrastructure.Database import Base
from app.Objects.UserRoleModel import UserRoleBase, SmallUserRoleBase


class User(Base):
    __tablename__ = "Users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    # Auth info
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, server_default=sql.expression.true())

    # ✅ Додаємо ForeignKey до UserRoles.id
    role_id = Column(UUID(as_uuid=True), ForeignKey("UserRoles.id", ondelete="SET NULL"), nullable=True)
    role = relationship("UserRole", backref=backref("users", lazy="selectin"))

    supervisor_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True, default=[])

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    birthday = Column(DateTime(timezone=True), nullable=True)

    # Session / identity
    temp_token = Column(UUID(as_uuid=True), unique=True, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now())




class SmallUserBase(BaseModel):
    id: uuid.UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    role: Optional[SmallUserRoleBase] = None
    created_at: datetime
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    id: uuid.UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    role: Optional[UserRoleBase] = None
    avatar_url: str | None
    birthday: datetime | None
    temp_token: uuid.UUID | None
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class MeUserBase(UserBase):
    id: uuid.UUID
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    class Config:
        from_attributes = True