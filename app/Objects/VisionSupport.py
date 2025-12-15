from sqlalchemy import (
    Column,
    BigInteger,
    String,
    ARRAY,
    Text,
    ForeignKey,
    TIMESTAMP,
    Boolean,
    Integer, UUID,
    func
)
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base


class VisionSupportUser(Base):
    __tablename__ = "VisionSupportUsers"

    telegram_id = Column(BigInteger, primary_key=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    last_message_text = Column(Text, nullable=True)

    new_messages = Column(Integer, nullable=True, default=0)

    created_at = Column(
        TIMESTAMP(timezone=True),
        default=func.now(),
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    messages = relationship("VisionSupportMessage", back_populates="user")
    answers = relationship("VisionSupportAnswer", back_populates="user")


class VisionSupportMessage(Base):
    __tablename__ = "VisionSupportMessages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    telegram_user_id = Column(
        BigInteger,
        ForeignKey("VisionSupportUsers.telegram_id"),
        nullable=False
    )

    text = Column(Text, nullable=False)
    files = Column(ARRAY(String))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("VisionSupportUser", back_populates="messages")


class VisionSupportAnswer(Base):
    __tablename__ = "VisionSupportAnswers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )

    telegram_user_id = Column(
        BigInteger,
        ForeignKey("VisionSupportUsers.telegram_id"),
        nullable=False
    )

    operator_id = Column(
        UUID(as_uuid=True),
        nullable=False
    )

    text = Column(Text, nullable=False)
    files = Column(ARRAY(String))

    is_sent_to_telegram = Column(Boolean, default=False, nullable=False)
    tried_to_send = Column(Integer, default=0, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("VisionSupportUser", back_populates="answers")