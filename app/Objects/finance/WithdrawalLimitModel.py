from sqlalchemy import Column, func, UUID, ForeignKey, Float, DateTime

from app.Infrastructure.Database import Base


class WithdrawalLimitModel(Base):
    __tablename__ = "WithdrawalLimits"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"),nullable=False)
    limit_amount = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())