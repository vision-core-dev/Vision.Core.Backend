import enum

from sqlalchemy import Column, Text, UUID, func, DateTime, Boolean, ForeignKey, String

from app.Infrastructure.Database import Base


class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    withdrawal = "withdrawal"
    deduction = "deduction"


class Transaction(Base):
    __tablename__ = "Transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    name = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)
    amount = Column(String(50), nullable=False)

    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id"))

    is_removed = Column(Boolean, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())