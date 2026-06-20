import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, func, ForeignKey
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel
from app.Objects.UserModel import UserShort


class GameFeedPost(Base):
    __tablename__ = "GameFeedPosts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    game_id = Column(UUID(as_uuid=True), ForeignKey("Games.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True)

    # Optional developer (studio or person) shown as the post's author instead of
    # the real creator. Plain slug, resolved on the frontend against the developers
    # list — mirrors Game.developer_slug (no DB-level FK).
    developer_slug = Column(String(100), nullable=True, index=True)

    title = Column(String(255), nullable=True)
    content = Column(TEXT, nullable=False)  # HTML from tiptap, sanitized server-side
    is_published = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("User", lazy="selectin")


class GameFeedPostBase(PydModel):
    id: uuid.UUID
    game_id: uuid.UUID
    author_id: uuid.UUID | None = None
    developer_slug: str | None = None
    title: str | None = None
    content: str
    is_published: bool = True
    created_at: datetime
    updated_at: datetime


class GameFeedPostWithAuthor(GameFeedPostBase):
    author: UserShort | None = None
