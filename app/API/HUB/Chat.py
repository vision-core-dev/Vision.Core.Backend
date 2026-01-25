"""
API для чатів
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.ChatService import ChatService
from app.Objects.ChatSchemas import (
    DirectChatCreate,
    GroupChatCreate,
    ChatUpdate,
    MessageCreate,
    AddMemberRequest,
    MarkReadRequest,
    ChatResponse,
    ChatListResponse,
    MessageResponse,
    MessagesListResponse,
    ChatMemberResponse,
    UserShortResponse,
)
from app.Objects.UserModel import User
from app.API.HUB.chat_websocket import get_chat_manager

chat_router = APIRouter(prefix="/Chat", tags=["Chat"])


def chat_to_response(chat, user_id: uuid.UUID = None, unread_count: int = 0) -> dict:
    """Convert Chat model to response dict"""
    if not chat:
        return None

    members = None
    if chat.members:
        members = [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "role": m.role.value,
                "notifications_enabled": m.notifications_enabled,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "user": {
                    "id": str(m.user.id),
                    "first_name": m.user.first_name,
                    "last_name": m.user.last_name,
                    "avatar_url": m.user.avatar_url,
                } if m.user else None
            }
            for m in chat.members
        ]

    last_message = None
    if hasattr(chat, 'last_message') and chat.last_message:
        last_message = chat.last_message.to_dict(include_sender=True, include_reply=False)

    return {
        "id": str(chat.id),
        "chat_type": chat.chat_type.value,
        "name": chat.name,
        "avatar_url": chat.avatar_url,
        "created_by_id": str(chat.created_by_id) if chat.created_by_id else None,
        "is_active": chat.is_active,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
        "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
        "members": members,
        "last_message": last_message,
        "unread_count": unread_count,
    }


@chat_router.get("/List", response_model=ChatListResponse)
async def get_chats(
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Отримати список чатів поточного користувача"""
    service = ChatService(db)
    chats = await service.get_user_chats(user.id)

    # Get unread counts for each chat
    chat_responses = []
    for chat in chats:
        unread_count = await service.get_unread_count(chat.id, user.id)
        chat_responses.append(chat_to_response(chat, user.id, unread_count))

    return {
        "chats": chat_responses,
        "total": len(chat_responses),
    }


@chat_router.post("/Direct", response_model=ChatResponse)
async def create_direct_chat(
    data: DirectChatCreate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Створити або отримати особистий чат з користувачем"""
    service = ChatService(db)

    try:
        chat = await service.get_or_create_direct_chat(user.id, uuid.UUID(data.user_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return chat_to_response(chat, user.id)


@chat_router.post("/Group", response_model=ChatResponse)
async def create_group_chat(
    data: GroupChatCreate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Створити груповий чат"""
    service = ChatService(db)

    try:
        member_ids = [uuid.UUID(mid) for mid in data.member_ids]
        chat = await service.create_group_chat(
            name=data.name,
            creator_id=user.id,
            member_ids=member_ids,
            avatar_url=data.avatar_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return chat_to_response(chat, user.id)


@chat_router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Отримати інформацію про чат"""
    service = ChatService(db)

    try:
        chat = await service.get_chat(uuid.UUID(chat_id), user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    unread_count = await service.get_unread_count(chat.id, user.id)
    return chat_to_response(chat, user.id, unread_count)


@chat_router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    data: ChatUpdate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Оновити чат (тільки групові)"""
    service = ChatService(db)

    try:
        chat = await service.update_chat(
            chat_id=uuid.UUID(chat_id),
            user_id=user.id,
            name=data.name,
            avatar_url=data.avatar_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return chat_to_response(chat, user.id)


@chat_router.get("/{chat_id}/Messages", response_model=MessagesListResponse)
async def get_messages(
    chat_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Отримати повідомлення чату"""
    service = ChatService(db)

    try:
        messages, total, has_more = await service.get_messages(
            chat_id=uuid.UUID(chat_id),
            user_id=user.id,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "messages": [msg.to_dict(include_sender=True, include_reply=True) for msg in messages],
        "total": total,
        "has_more": has_more,
    }


@chat_router.post("/{chat_id}/Messages", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Відправити повідомлення в чат"""
    service = ChatService(db)

    try:
        reply_to_id = uuid.UUID(data.reply_to_id) if data.reply_to_id else None
        message = await service.send_message(
            chat_id=uuid.UUID(chat_id),
            sender_id=user.id,
            content=data.content,
            reply_to_id=reply_to_id,
            message_type=data.message_type,
            attachment_url=data.attachment_url,
            attachment_name=data.attachment_name,
            attachment_size=data.attachment_size,
            audio_duration=data.audio_duration,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcast message via WebSocket to other chat members
    message_data = message.to_dict(include_sender=True, include_reply=True)
    chat_manager = get_chat_manager()
    await chat_manager.broadcast_new_message(chat_id, message_data, sender_id=str(user.id))

    return message_data


@chat_router.post("/{chat_id}/Members")
async def add_member(
    chat_id: str,
    data: AddMemberRequest,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Додати учасника до групового чату"""
    service = ChatService(db)

    try:
        await service.add_member(
            chat_id=uuid.UUID(chat_id),
            user_id=user.id,
            new_member_id=uuid.UUID(data.user_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "message": "Member added successfully"}


@chat_router.delete("/{chat_id}/Members/{member_id}")
async def remove_member(
    chat_id: str,
    member_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Видалити учасника з групового чату"""
    service = ChatService(db)

    try:
        await service.remove_member(
            chat_id=uuid.UUID(chat_id),
            user_id=user.id,
            member_id=uuid.UUID(member_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "message": "Member removed successfully"}


@chat_router.post("/{chat_id}/Read")
async def mark_as_read(
    chat_id: str,
    data: MarkReadRequest,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Позначити повідомлення як прочитане"""
    service = ChatService(db)

    try:
        await service.mark_as_read(
            chat_id=uuid.UUID(chat_id),
            user_id=user.id,
            message_id=uuid.UUID(data.message_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "message": "Marked as read"}
