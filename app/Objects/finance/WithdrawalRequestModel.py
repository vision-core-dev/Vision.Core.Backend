import enum

from sqlalchemy import Column, UUID, String, DateTime, ForeignKey, func, BigInteger

from app.Infrastructure.Database import Base


class WithdrawalRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"

class WithdrawalRequest(Base):
    __tablename__ = "WithdrawalRequests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)

    amount = Column(BigInteger, nullable=False)
    status = Column(String(50), nullable=False, server_default="pending")

    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
