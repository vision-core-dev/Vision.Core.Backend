import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, func, ARRAY, ForeignKey
from sqlalchemy.orm import relationship
from app.Infrastructure.Database import Base, PydModel
from app.Objects.UserModel import UserShort

class News(Base):
    __tablename__ = "News"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    author_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255), nullable=True)
    content = Column(TEXT, nullable=False) # Store HTML/Rich text
    
    # Store labels as array of strings
    labels = Column(ARRAY(TEXT), nullable=True, default=[])
    
    # Optional target for links
    target_text = Column(String(100), nullable=True)
    target_url = Column(TEXT, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author = relationship("User", lazy="selectin")

class NewsBase(PydModel):
    id: uuid.UUID
    author_id: uuid.UUID
    title: str | None = None
    content: str
    labels: list[str] = []
    target_text: str | None = None
    target_url: str | None = None
    created_at: datetime
    updated_at: datetime

class NewsWithAuthor(NewsBase):
    author: UserShort
