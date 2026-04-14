import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UUID, TEXT, Boolean, func

from app.Infrastructure.Database import Base, PydModel


class ContactRequest(Base):
    __tablename__ = "ContactRequests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    category = Column(String(50), nullable=False)
    category_label = Column(String(255), nullable=False)

    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    telegram = Column(String(100), nullable=True)

    message = Column(TEXT, nullable=False)

    is_handled = Column(Boolean, nullable=False, default=False)

    ip_address = Column(String(64), nullable=True)
    user_agent = Column(TEXT, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ContactRequestBase(PydModel):
    id: uuid.UUID
    category: str
    category_label: str
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    message: str
    is_handled: bool = False
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
