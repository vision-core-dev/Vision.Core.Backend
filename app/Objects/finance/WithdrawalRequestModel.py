import enum
from sqlalchemy import Column, UUID, DateTime, ForeignKey, func, Float, Text
from sqlalchemy.dialects.postgresql import ENUM
from app.Infrastructure.Database import Base


class WithdrawalRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


# ✅ Створюємо єдиний ENUM-тип
WithdrawalRequestStatusEnum = ENUM(
    WithdrawalRequestStatus,
    name="withdrawalrequeststatus",
    create_type=True
)


class WithdrawalRequest(Base):
    __tablename__ = "WithdrawalRequests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)

    # 👇 Використовуємо вже створений тип
    status = Column(
        WithdrawalRequestStatusEnum,
        nullable=False,
        server_default="PENDING"
    )

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
