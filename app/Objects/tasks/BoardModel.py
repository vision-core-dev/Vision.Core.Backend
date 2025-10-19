import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, UUID, String, Table, ForeignKey, func, DateTime, Text
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base


class Board(Base):
    __tablename__ = "Boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.now())

    # Доступні учасники (many-to-many)
    members = relationship("User", secondary="BoardMembers", back_populates="boards")

BoardMember = Table(
    "BoardMembers",
    Base.metadata,
    Column("board_id", UUID(as_uuid=True), ForeignKey("Boards.id")),
    Column("user_id", UUID(as_uuid=True), ForeignKey("Users.id")),
    Column("role", String(50), default="member")
)
