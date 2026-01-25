"""
Pydantic схеми для чатів
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# === Request Schemas ===

class DirectChatCreate(BaseModel):
    """Створення особистого чату"""
    user_id: str = Field(..., description="ID користувача для чату")


class GroupChatCreate(BaseModel):
    """Створення групового чату"""
    name: str = Field(..., min_length=1, max_length=200, description="Назва групи")
    member_ids: List[str] = Field(default=[], description="ID учасників")
    avatar_url: Optional[str] = None


class ChatUpdate(BaseModel):
    """Оновлення чату"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    avatar_url: Optional[str] = None


class MessageCreate(BaseModel):
    """Створення повідомлення"""
    content: str = Field(..., min_length=1, max_length=10000)
    reply_to_id: Optional[str] = None


class AddMemberRequest(BaseModel):
    """Додавання учасника"""
    user_id: str


class MarkReadRequest(BaseModel):
    """Позначити повідомлення прочитаним"""
    message_id: str


# === Response Schemas ===

class UserShortResponse(BaseModel):
    """Короткий опис користувача"""
    id: str
    first_name: str
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None


class ChatMemberResponse(BaseModel):
    """Учасник чату"""
    id: str
    user_id: str
    role: str
    notifications_enabled: bool
    joined_at: str
    user: Optional[UserShortResponse] = None


class MessageResponse(BaseModel):
    """Повідомлення"""
    id: str
    chat_id: str
    sender_id: Optional[str] = None
    content: str
    reply_to_id: Optional[str] = None
    is_system: bool
    is_deleted: bool
    created_at: str
    updated_at: str
    sender: Optional[UserShortResponse] = None
    reply_to: Optional["MessageResponse"] = None


class ChatResponse(BaseModel):
    """Чат"""
    id: str
    chat_type: Literal["direct", "group"]
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by_id: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    members: Optional[List[ChatMemberResponse]] = None
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0


class ChatListResponse(BaseModel):
    """Список чатів"""
    chats: List[ChatResponse]
    total: int


class MessagesListResponse(BaseModel):
    """Список повідомлень"""
    messages: List[MessageResponse]
    total: int
    has_more: bool


# Update forward references
MessageResponse.model_rebuild()
