import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, func

from app.Infrastructure.Database import Base, PydModel

class Game(Base):
    __tablename__ = "Games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    slug = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(TEXT, nullable=True)
    content = Column(TEXT, nullable=False)
    thumbnail_url = Column(TEXT, nullable=True)
    play_url = Column(TEXT, nullable=True)
    is_published = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class GameBase(PydModel):
    id: uuid.UUID
    slug: str
    title: str
    summary: str | None = None
    content: str
    thumbnail_url: str | None = None
    play_url: str | None = None
    is_published: bool = True
    created_at: datetime
    updated_at: datetime
