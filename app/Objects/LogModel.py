import uuid

from sqlalchemy import Column, func, DateTime, TEXT, String, UUID, ForeignKey

from app.Infrastructure.Database import Base


class Log(Base):
    __tablename__ = "Logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    actor_id = Column(UUID(as_uuid=True), ForeignKey(), nullable=True)

    entity_type = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)

    action = Column(String(100), nullable=False)
    details = Column(TEXT, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())