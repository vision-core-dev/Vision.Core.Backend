from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.Infrastructure.Database import Base, PydModel


class TaskTag(Base):
    __tablename__ = "TaskTags"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    color = Column(String(7), nullable=False)  # Hex color code, e.g. #FF5733
    board_id = Column(UUID(as_uuid=True), ForeignKey("Boards.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TaskTagBase(PydModel):
    id: UUID
    name: str
    color: str