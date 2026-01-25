"""
Моделі для чату: Chat, ChatMember, Message
"""
import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy import func

from app.Infrastructure.Database import Base


class ChatType(str, enum.Enum):
    """Тип чату"""
    DIRECT = "direct"  # Особистий чат (1-на-1)
    GROUP = "group"    # Груповий чат


class ChatMemberRole(str, enum.Enum):
    """Роль учасника в чаті"""
    ADMIN = "admin"    # Адміністратор (може керувати учасниками)
    MEMBER = "member"  # Звичайний учасник


class Chat(Base):
    """
    Чат (розмова).
    Може бути особистим (direct) або груповим (group).
    """
    __tablename__ = "Chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Тип чату
    chat_type = Column(SQLEnum(ChatType), nullable=False, default=ChatType.DIRECT)
    
    # Назва (тільки для групових чатів)
    name = Column(String(200), nullable=True)
    
    # Аватар групи (тільки для групових чатів)
    avatar_url = Column(String(500), nullable=True)
    
    # Хто створив чат
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True)
    
    # Чи активний чат
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    members = relationship("ChatMember", back_populates="chat", lazy="selectin", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat", lazy="dynamic", cascade="all, delete-orphan")
    
    def __repr__(self):
        if self.chat_type == ChatType.GROUP:
            return f"<Chat Group '{self.name}'>"
        return f"<Chat Direct {self.id}>"


class ChatMember(Base):
    """
    Учасник чату.
    Зв'язує користувачів з чатами.
    """
    __tablename__ = "ChatMembers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Зв'язки
    chat_id = Column(UUID(as_uuid=True), ForeignKey("Chats.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Роль в чаті
    role = Column(SQLEnum(ChatMemberRole), nullable=False, default=ChatMemberRole.MEMBER)
    
    # ID останнього прочитаного повідомлення (для unread count)
    last_read_message_id = Column(UUID(as_uuid=True), ForeignKey("Messages.id", ondelete="SET NULL"), nullable=True)
    
    # Чи отримує сповіщення
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    chat = relationship("Chat", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id], lazy="selectin")
    
    def __repr__(self):
        return f"<ChatMember user={self.user_id} chat={self.chat_id}>"


class Message(Base):
    """
    Повідомлення в чаті.
    """
    __tablename__ = "Messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Зв'язки
    chat_id = Column(UUID(as_uuid=True), ForeignKey("Chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Контент повідомлення
    content = Column(Text, nullable=True)  # Can be null for audio-only messages
    
    # Тип повідомлення
    message_type = Column(String(20), nullable=False, default="text")  # text, audio, image, file
    
    # Вкладення (для аудіо, зображень, файлів)
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_size = Column(Integer, nullable=True)  # in bytes
    audio_duration = Column(Integer, nullable=True)  # in seconds for audio messages
    
    # Відповідь на інше повідомлення (опційно)
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("Messages.id", ondelete="SET NULL"), nullable=True)
    
    # Чи системне повідомлення (наприклад, "User joined the chat")
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Чи видалено (soft delete)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], lazy="selectin")
    reply_to = relationship("Message", remote_side=[id], lazy="selectin")
    
    def __repr__(self):
        return f"<Message {self.id} in chat {self.chat_id}>"
    
    def to_dict(self, include_sender=True, include_reply=False):
        """Конвертація в словник для API"""
        data = {
            "id": str(self.id),
            "chat_id": str(self.chat_id),
            "sender_id": str(self.sender_id) if self.sender_id else None,
            "content": self.content if not self.is_deleted else "[Повідомлення видалено]",
            "message_type": self.message_type,
            "attachment_url": self.attachment_url,
            "attachment_name": self.attachment_name,
            "attachment_size": self.attachment_size,
            "audio_duration": self.audio_duration,
            "reply_to_id": str(self.reply_to_id) if self.reply_to_id else None,
            "is_system": self.is_system,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sender and self.sender:
            data["sender"] = {
                "id": str(self.sender.id),
                "first_name": self.sender.first_name,
                "last_name": self.sender.last_name,
                "avatar_url": self.sender.avatar_url,
            }
        
        if include_reply and self.reply_to:
            data["reply_to"] = self.reply_to.to_dict(include_sender=True, include_reply=False)
        
        return data
