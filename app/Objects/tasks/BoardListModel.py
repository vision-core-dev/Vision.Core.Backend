import uuid
from datetime import datetime

from sqlalchemy import Column, UUID, String, Integer, func, DateTime, ForeignKey

from app.Infrastructure.Database import Base


class BoardList(Base):
    __tablename__ = "BoardLists"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    board_id = Column(UUID(as_uuid=True), ForeignKey("Boards.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=0)  # порядок у канбані
    color = Column(String(20), nullable=True)  # опціонально

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=datetime.now())