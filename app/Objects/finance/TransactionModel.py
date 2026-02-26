import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UUID, func, DateTime, Boolean, ForeignKey, String, Float
from sqlalchemy.dialects.postgresql import ENUM
from app.Infrastructure.Database import Base, PydModel


class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    DEDUCTION = "deduction"


# ✅ Оголошуємо ENUM тип для PostgreSQL
TransactionTypeEnum = ENUM(
    TransactionType,
    name="transactiontype",     # ім’я типу в PostgreSQL
    create_type=True            # створює тип, якщо його ще немає
)


class Transaction(Base):
    __tablename__ = "Transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    name = Column(Text, nullable=True)
    type = Column(TransactionTypeEnum, nullable=False)
    amount = Column(Float, nullable=False)

    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("Tasks.id", ondelete="SET NULL"), nullable=True)

    is_future = Column(Boolean, default=False, server_default="false")
    is_removed = Column(Boolean, default=False, server_default="false")

    transaction_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TransactionBase(PydModel):
    id: uuid.UUID
    name: str
    type: TransactionType
    amount: float
    task_id: uuid.UUID | None = None
    transaction_at: datetime