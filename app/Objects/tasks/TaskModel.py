import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, ForeignKey, DateTime, Boolean, Numeric, String, Text, func, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel


class TaskStatus(enum.Enum):
    backlog = "backlog"
    in_progress = "in_progress"
    review = "review"
    done = "done"

class TaskPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Task(Base):
    __tablename__ = "Tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id"), nullable=True)

    board_id = Column(UUID(as_uuid=True), ForeignKey("Boards.id", ondelete="SET NULL"), nullable=True)
    list_id = Column(UUID(as_uuid=True), ForeignKey("BoardLists.id", ondelete="SET NULL"), nullable=True)
    order = Column(BigInteger, nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))

    value_uah = Column(Numeric(10, 2), default=0.00)
    penalty_uah = Column(Numeric(10, 2), default=0.00)
    is_accrued = Column(Boolean, default=False) # чи нараховано

    started_at = Column(DateTime, nullable=True)
    deadline_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    status = Column(ENUM(TaskStatus), default=TaskStatus.backlog)
    priority = Column(ENUM(TaskPriority), default=TaskPriority.low)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.now())

    board = relationship("Board", backref="Tasks")
    list = relationship("BoardList", backref="Tasks")
    created_by = relationship("User", foreign_keys=[created_by_id])
    assignees = relationship("TaskAssignee", back_populates="task", cascade="all, delete-orphan")


class TaskAssignee(Base):
    __tablename__ = "TaskAssignees"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"))

    role = Column(String(50), nullable=True)  # наприклад: "lead", "support"
    share = Column(Numeric(5, 2), nullable=True)  # опціонально: % участі (0.0–1.0)

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="assignees")
    user = relationship("User", back_populates="assigned_tasks")

# for assignee in task.assignees:
#     payout = task.value_uah * (assignee.share or 1 / len(task.assignees))

class TaskPreview(PydModel):
    id: uuid.UUID
    title: str
    status: TaskStatus
    priority: TaskPriority
    assigned_to_id: uuid.UUID | None
    deadline_at: datetime | None