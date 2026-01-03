import uuid

from sqlalchemy import Column, func, DateTime, TEXT, String, UUID, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from app.Infrastructure.Database import Base


class Form(Base):
    __tablename__ = "Forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=True)

    slug = Column(String(200), unique=True, nullable=False)
    title = Column(String(200), nullable=False)

    is_anonymous = Column(Boolean, server_default="false")

    data = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FormResult(Base):
    __tablename__ = "FormResults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    form_id = Column(UUID(as_uuid=True), ForeignKey("Forms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"), nullable=True)

    data = Column(JSONB, nullable=True)

    submitted_at = Column(DateTime(timezone=True), server_default=func.now())