import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, String, ForeignKey, func, DateTime, Text, Boolean, JSON

from app.Infrastructure.Database import Base, PydModel


class BoardRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Board(Base):
    __tablename__ = "Boards"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    banner_url = Column(Text, nullable=True)

    members = Column(JSON, nullable=False, default=dict, server_default="{}")

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))

    is_removed = Column(Boolean, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BoardBase(PydModel):
    id: uuid.UUID
    name: str
    description: str | None
    banner_url: str | None
    members: dict | None = {}
    created_at: datetime | None

# ✅ Pydantic-схема для відповіді
class BoardPreview(PydModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
