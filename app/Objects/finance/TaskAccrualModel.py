import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UUID, func, DateTime, Boolean, ForeignKey, Float, String
from app.Infrastructure.Database import Base, PydModel


class TaskAccrual(Base):
    __tablename__ = "TaskAccruals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=True)

    name = Column(String(255), nullable=True, default="Виплата за задачу")
    amount = Column(Float, nullable=False)

    is_removed = Column(Boolean, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskAccrualBase(PydModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    name: str | None = None
    amount: float
    created_at: datetime
