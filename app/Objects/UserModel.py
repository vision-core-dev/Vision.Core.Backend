import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, UUID, func, ARRAY, ForeignKey, Boolean, sql, Numeric, Integer, TEXT, \
    Float
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship, backref

from app.Infrastructure.Database import Base, PydModel


class Currency(enum.Enum):
    UAH = "UAH"
    USD = "USD"
    EUR = "EUR"

class PaymentMethod(enum.Enum):
    STEAM_GAME = "steam_game"
    BANK_TRANSFER = "bank_transfer"
    ROBUX = "robux"
    PAYPAL = "paypal"

class User(Base):
    __tablename__ = "Users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    # Auth info
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)

    balance = Column(Float, nullable=False, default=0.00)
    withdrawn_amount = Column(Float, nullable=False, default=0.00, server_default="0.00")
    currency = Column(ENUM(Currency), nullable=False, server_default="UAH")

    is_active = Column(Boolean, nullable=False, server_default=sql.expression.true())
    is_balance_visible = Column(Boolean, nullable=False, server_default=sql.expression.false())

    is_need_accept_terms = Column(Boolean, nullable=False, server_default=sql.expression.true())
    is_terms_accepted = Column(Boolean, nullable=False, server_default=sql.expression.false())
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)

    # ✅ Додаємо ForeignKey до UserRoles.id
    role_id = Column(UUID(as_uuid=True), ForeignKey("UserRoles.id", ondelete="SET NULL"), nullable=True)
    role = relationship("UserRole", lazy="selectin", backref=backref("users", lazy="selectin"))

    supervisor_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True, default=[])

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    birthday = Column(DateTime(timezone=True), nullable=True)

    # OAuth linked accounts
    google_id = Column(String(100), unique=True, nullable=True)
    google_email = Column(String(255), nullable=True)
    discord_id = Column(String(100), unique=True, nullable=True)
    discord_username = Column(String(255), nullable=True)
    telegram_id = Column(String(100), unique=True, nullable=True)
    telegram_username = Column(String(255), nullable=True)
    roblox_id = Column(String(100), unique=True, nullable=True)
    roblox_username = Column(String(255), nullable=True)

    # Notification preferences
    notify_discord = Column(Boolean, nullable=False, server_default=sql.expression.false())
    notify_telegram = Column(Boolean, nullable=False, server_default=sql.expression.false())

    # Active badge emoji (displayed next to name)
    active_badge_emoji = Column(String(10), nullable=True)

    # Session / identity
    temp_token = Column(UUID(as_uuid=True), unique=True, nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now())



class UserRole(Base):
    __tablename__ = "UserRoles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(50), unique=True, nullable=False)

    menu = Column(ARRAY(TEXT), nullable=False, default=[])
    order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now())

class UserRolePreview(PydModel):
    id: uuid.UUID
    key: str
    name: str

class UserRoleBase(PydModel):
    id: uuid.UUID
    key: str
    name: str
    menu: list[str]
    order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MyUserRoleBase(PydModel):
    id: uuid.UUID
    key: str
    name: str
    menu: list[str]
    order: int

class UserRoleCreate(PydModel):
    key: str
    name: str
    menu: list[str] = []
    order: int = 0

class UserRoleUpdate(PydModel):
    key: Optional[str] = None
    name: Optional[str] = None
    menu: Optional[list[str]] = None
    order: Optional[int] = None
class UserShort(PydModel):
    id: uuid.UUID
    first_name: str
    last_name: str | None = None
    avatar_url: str | None = None
    active_badge_emoji: str | None = None

class UserPreview(PydModel):
    id: uuid.UUID
    email: str | None = None
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    birthday: datetime | None = None
    role: Optional[UserRolePreview] = None
    role_name: str | None = None
    is_active: bool = False
    created_at: datetime | None = None
    active_badge_emoji: str | None = None
    discord_username: str | None = None
    telegram_username: str | None = None
    board_names: list[str] = []

class UserBase(PydModel):
    id: uuid.UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    balance: float
    withdrawn_amount: float
    role: Optional[UserRoleBase] = None
    avatar_url: str | None
    birthday: datetime | None
    is_active: bool
    temp_token: uuid.UUID | None
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime | None = None
    active_badge_emoji: str | None = None
    google_id: Optional[str] = None
    google_email: Optional[str] = None
    discord_id: Optional[str] = None
    discord_username: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None
    roblox_id: Optional[str] = None
    roblox_username: Optional[str] = None

class MeUserBase(PydModel):
    id: uuid.UUID
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    birthday: datetime | None
    is_balance_visible: bool
    balance: float
    is_need_accept_terms: bool
    is_terms_accepted: bool
    terms_accepted_at: Optional[datetime]
    is_active: bool
    notify_discord: bool = False
    notify_telegram: bool = False
    active_badge_emoji: str | None = None
    google_id: Optional[str] = None
    google_email: Optional[str] = None
    discord_id: Optional[str] = None
    discord_username: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None
    roblox_id: Optional[str] = None
    roblox_username: Optional[str] = None