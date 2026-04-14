import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, func, ARRAY

from app.Infrastructure.Database import Base, PydModel


class Job(Base):
    __tablename__ = "Jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    slug = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(TEXT, nullable=False)  # HTML from tiptap

    salary = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    employment_type = Column(String(100), nullable=True)  # Full-time, Contract, ...
    tags = Column(ARRAY(TEXT), nullable=True, default=[])

    apply_url = Column(TEXT, nullable=True)

    is_published = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class JobBase(PydModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    salary: str | None = None
    location: str | None = None
    employment_type: str | None = None
    tags: list[str] = []
    apply_url: str | None = None
    is_published: bool = True
    created_at: datetime
    updated_at: datetime
