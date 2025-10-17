import enum
import uuid
from datetime import datetime, time

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, UUID, TEXT, func, Time

from app.Infrastructure.Database import Base


class EventInviteStatus(enum.Enum):
    PENDING = "pending"      # запрошення надіслано
    ACCEPTED = "accepted"    # користувач підтвердив участь
    DECLINED = "declined"    # відмовився
    NO_SHOW = "no_show"      # не прийшов, хоча прийняв
    ATTENDED = "attended"    # прийшов


class Event(Base):
    __tablename__ = "Events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    name = Column(String(100), nullable=False)
    description = Column(TEXT, nullable=True)

    # 📅 Основна дата події (можна без часу)
    date = Column(DateTime, nullable=False)

    # 🕐 Час початку і кінця — краще використовувати `Time`, а не `DateTime`
    time_from = Column(Time, nullable=False)
    time_to = Column(Time, nullable=False)

    location = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EventInvite(Base):
    __tablename__ = "EventInvites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    event_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    status = Column(String(50), nullable=False, server_default=EventInviteStatus.PENDING.value)

    # 📝 Причина відмови або неявки
    reason = Column(TEXT, nullable=True)

    # 📆 Фактичний час коли користувач прибув (якщо прийшов)
    attended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class EventBase(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    date: datetime
    time_from: time
    time_to: time
    location: str | None
    created_at: datetime

    class Config:
        from_attributes = True