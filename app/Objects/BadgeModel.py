import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, func, UUID, String, TEXT, ForeignKey
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base


class Badge(Base):
    __tablename__ = "Badges"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    description = Column(TEXT, nullable=True)

    icon_url = Column(String(255), nullable=True)
    emoji = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserBadge(Base):
    __tablename__ = "UserBadges"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False)

    badge_id = Column(UUID(as_uuid=True), ForeignKey("Badges.id", ondelete="CASCADE"), nullable=False)
    badge = relationship("Badge", backref="user_badges")

    awarded_at = Column(DateTime(timezone=True), server_default=func.now())

class UserBadgeBase(BaseModel):
    id: uuid.UUID       
    name: str
    description: str | None
    icon_url: str | None
    emoji: str | None
    awarded_at: datetime | None

    class Config:
        from_attributes = True