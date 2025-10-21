import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, String, ForeignKey, func, DateTime, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel
from app.Objects.UserModel import User


class BoardRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Board(Base):
    __tablename__ = "Boards"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # many-to-many
    members = relationship(User, secondary="BoardMembers", back_populates="boards")


class BoardMember(Base):
    __tablename__ = "BoardMembers"

    board_id = Column(UUID(as_uuid=True), ForeignKey("Boards.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), primary_key=True)
    role = Column(ENUM(BoardRole), default=BoardRole.MEMBER)


# ✅ Pydantic-схема для відповіді
class BoardBase(PydModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True
