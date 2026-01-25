import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, func, DateTime, TEXT, String, UUID, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import relationship

from app.Infrastructure.Database import Base, PydModel


class ActionType(enum.Enum):
    """Типи дій для логування"""
    # CRUD операції
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    
    # Операції з доступом
    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    
    # Операції з правами
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    CHANGE_ROLE = "change_role"
    
    # Операції з статусами
    STATUS_CHANGE = "status_change"
    ARCHIVE = "archive"
    UNARCHIVE = "unarchive"
    
    # Операції з завданнями
    ASSIGN = "assign"
    UNASSIGN = "unassign"
    MOVE = "move"
    COMPLETE = "complete"
    REOPEN = "reopen"
    
    # Інші операції
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"


class Log(Base):
    """
    Глобальна таблиця логів для всіх операцій в системі.
    Зберігає детальну інформацію про всі дії користувачів.
    """
    __tablename__ = "Logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())

    # Хто виконав дію
    actor_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Над чим виконана дія
    entity_type = Column(String(100), nullable=False, index=True)  # Task, Board, User, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    entity_name = Column(String(500), nullable=True)  # Назва сутності для зручності

    # Що було зроблено
    action = Column(ENUM(ActionType), nullable=False, index=True)
    
    # Деталі зміни
    old_values = Column(JSONB, nullable=True)  # Старі значення полів
    new_values = Column(JSONB, nullable=True)  # Нові значення полів
    changed_fields = Column(JSONB, nullable=True)  # Список змінених полів
    
    # Додаткова інформація
    details = Column(TEXT, nullable=True)  # Текстовий опис дії
    extra_data = Column(JSONB, nullable=True)  # Додаткові метадані
    
    # Технічна інформація
    ip_address = Column(String(45), nullable=True)  # IPv4 або IPv6
    user_agent = Column(TEXT, nullable=True)
    request_id = Column(String(100), nullable=True)  # Для трейсингу
    
    # Часові мітки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    actor = relationship("User", foreign_keys=[actor_id], backref="activity_logs")

    __table_args__ = (
        # Композитні індекси для швидкого пошуку
        Index('idx_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_logs_actor_action', 'actor_id', 'action'),
        Index('idx_logs_created_at_desc', created_at.desc()),
    )


class LogResponse(PydModel):
    """Pydantic модель для відповіді з логом"""
    id: uuid.UUID
    actor_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID
    entity_name: str | None
    action: ActionType
    old_values: dict | None
    new_values: dict | None
    changed_fields: list | None
    details: str | None
    extra_data: dict | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class LogListResponse(PydModel):
    """Pydantic модель для списку логів"""
    logs: list[LogResponse]
    total: int
    page: int
    page_size: int