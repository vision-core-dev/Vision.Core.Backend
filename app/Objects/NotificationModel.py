import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, func, UUID, String, ForeignKey, TEXT, DateTime, Boolean

from app.Infrastructure.Database import Base


class UserNotif(Base):
    __tablename__ = "UserNotifs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=False)

    title = Column(String(100), nullable=False)
    message = Column(String(255), nullable=False)
    link = Column(TEXT, nullable=True)

    is_read = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MyNotifBase(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime | None

    class Config:
        from_attributes = True
