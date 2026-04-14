import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, func, ARRAY, ForeignKey
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel
from app.Objects.UserModel import UserShort


class BlogPost(Base):
    __tablename__ = "BlogPosts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True)

    slug = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(TEXT, nullable=True)
    content = Column(TEXT, nullable=False)  # HTML from tiptap
    thumbnail_url = Column(TEXT, nullable=True)

    category = Column(String(100), nullable=True)
    tags = Column(ARRAY(TEXT), nullable=True, default=[])
    reading_time = Column(String(50), nullable=True)

    is_anonymous = Column(Boolean, nullable=False, default=False)
    is_published = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("User", lazy="selectin")


class BlogPostBase(PydModel):
    id: uuid.UUID
    slug: str
    title: str
    summary: str | None = None
    content: str
    thumbnail_url: str | None = None
    category: str | None = None
    tags: list[str] = []
    reading_time: str | None = None
    is_anonymous: bool = False
    is_published: bool = True
    created_at: datetime
    updated_at: datetime


class BlogPostWithAuthor(BlogPostBase):
    author: UserShort | None = None
