import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, UUID, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel


class SubtaskStatus(enum.Enum):
    NO_STATUS = "no_status"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


class Subtask(Base):
    __tablename__ = "Subtasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="CASCADE"))
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True)  # 🆕

    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, server_default=SubtaskStatus.NO_STATUS.value)
    deadline_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task = relationship("Task", back_populates="subtasks", foreign_keys=[task_id])
    assignee = relationship("User", foreign_keys=[assignee_id])  # 🆕


class SubtaskBase(PydModel):
    id: uuid.UUID
    name: str
    status: SubtaskStatus
    deadline_at: Optional[datetime] = None
    assignee_id: Optional[uuid.UUID] = None