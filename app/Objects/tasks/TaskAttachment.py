import enum

from sqlalchemy import Column, DateTime, func, UUID, ForeignKey, Text, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base


class AttachmentType(enum.Enum):
    file = "file"
    link = "link"

class TaskAttachment(Base):
    __tablename__ = "TaskAttachments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="CASCADE"))

    type = Column(ENUM(AttachmentType), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", backref="attachments")


class TaskComment(Base):
    __tablename__ = "TaskComments"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))

    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", backref="comments")
    user = relationship("User")