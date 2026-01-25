"""
Сервіс для роботи з чатами
"""
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.Objects.ChatModel import Chat, ChatMember, Message, ChatType, ChatMemberRole
from app.Objects.UserModel import User


class ChatService:
    """Сервіс для управління чатами"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_chats(self, user_id: uuid.UUID) -> List[Chat]:
        """Отримати всі чати користувача"""
        query = (
            select(Chat)
            .join(ChatMember, Chat.id == ChatMember.chat_id)
            .where(
                and_(
                    ChatMember.user_id == user_id,
                    Chat.is_active == True
                )
            )
            .options(
                selectinload(Chat.members).selectinload(ChatMember.user),
                selectinload(Chat.created_by)
            )
            .order_by(desc(Chat.updated_at))
        )

        result = await self.db.execute(query)
        chats = result.scalars().unique().all()

        # Load last message for each chat
        for chat in chats:
            last_msg_query = (
                select(Message)
                .where(Message.chat_id == chat.id)
                .order_by(desc(Message.created_at))
                .limit(1)
                .options(selectinload(Message.sender))
            )
            last_msg_result = await self.db.execute(last_msg_query)
            chat.last_message = last_msg_result.scalar_one_or_none()

        return list(chats)

    async def get_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Chat]:
        """Отримати чат за ID (якщо користувач є учасником)"""
        query = (
            select(Chat)
            .join(ChatMember, Chat.id == ChatMember.chat_id)
            .where(
                and_(
                    Chat.id == chat_id,
                    ChatMember.user_id == user_id,
                    Chat.is_active == True
                )
            )
            .options(
                selectinload(Chat.members).selectinload(ChatMember.user),
                selectinload(Chat.created_by)
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_direct_chat(self, user1_id: uuid.UUID, user2_id: uuid.UUID) -> Chat:
        """Отримати або створити особистий чат між двома користувачами"""
        # Find existing direct chat
        query = (
            select(Chat)
            .join(ChatMember, Chat.id == ChatMember.chat_id)
            .where(
                and_(
                    Chat.chat_type == ChatType.DIRECT,
                    Chat.is_active == True,
                    ChatMember.user_id.in_([user1_id, user2_id])
                )
            )
            .group_by(Chat.id)
            .having(func.count(ChatMember.id) == 2)
            .options(
                selectinload(Chat.members).selectinload(ChatMember.user)
            )
        )

        result = await self.db.execute(query)
        existing_chat = result.scalar_one_or_none()

        if existing_chat:
            return existing_chat

        # Create new direct chat
        chat = Chat(
            chat_type=ChatType.DIRECT,
            created_by_id=user1_id
        )
        self.db.add(chat)
        await self.db.flush()

        # Add members
        member1 = ChatMember(
            chat_id=chat.id,
            user_id=user1_id,
            role=ChatMemberRole.MEMBER
        )
        member2 = ChatMember(
            chat_id=chat.id,
            user_id=user2_id,
            role=ChatMemberRole.MEMBER
        )
        self.db.add(member1)
        self.db.add(member2)

        await self.db.commit()

        # Reload with relationships
        return await self.get_chat(chat.id, user1_id)

    async def create_group_chat(
        self,
        name: str,
        creator_id: uuid.UUID,
        member_ids: List[uuid.UUID],
        avatar_url: Optional[str] = None
    ) -> Chat:
        """Створити груповий чат"""
        # Create chat
        chat = Chat(
            chat_type=ChatType.GROUP,
            name=name,
            avatar_url=avatar_url,
            created_by_id=creator_id
        )
        self.db.add(chat)
        await self.db.flush()

        # Add creator as admin
        creator_member = ChatMember(
            chat_id=chat.id,
            user_id=creator_id,
            role=ChatMemberRole.ADMIN
        )
        self.db.add(creator_member)

        # Add other members
        for member_id in member_ids:
            if member_id != creator_id:
                member = ChatMember(
                    chat_id=chat.id,
                    user_id=member_id,
                    role=ChatMemberRole.MEMBER
                )
                self.db.add(member)

        # Create system message
        system_msg = Message(
            chat_id=chat.id,
            content=f"Груповий чат «{name}» створено",
            is_system=True
        )
        self.db.add(system_msg)

        await self.db.commit()

        return await self.get_chat(chat.id, creator_id)

    async def get_messages(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Message], int, bool]:
        """Отримати повідомлення чату"""
        # Verify user is member
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        # Count total
        count_query = select(func.count(Message.id)).where(Message.chat_id == chat_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get messages
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Message.sender),
                selectinload(Message.reply_to).selectinload(Message.sender)
            )
        )

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        has_more = offset + len(messages) < total

        return messages, total, has_more

    async def send_message(
        self,
        chat_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: Optional[str],
        reply_to_id: Optional[uuid.UUID] = None,
        **kwargs
    ) -> Message:
        """Відправити повідомлення"""
        # Verify user is member
        chat = await self.get_chat(chat_id, sender_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        # Create message
        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
            **kwargs
        )
        self.db.add(message)

        # Update chat timestamp
        chat.updated_at = datetime.utcnow()

        await self.db.commit()

        # Reload with relationships
        query = (
            select(Message)
            .where(Message.id == message.id)
            .options(
                selectinload(Message.sender),
                selectinload(Message.reply_to).selectinload(Message.sender)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_chat(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Chat:
        """Оновити чат (тільки групові)"""
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        if chat.chat_type != ChatType.GROUP:
            raise ValueError("Only group chats can be updated")

        if name is not None:
            chat.name = name
        if avatar_url is not None:
            chat.avatar_url = avatar_url

        await self.db.commit()
        return await self.get_chat(chat_id, user_id)

    async def add_member(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        new_member_id: uuid.UUID
    ) -> ChatMember:
        """Додати учасника до групового чату"""
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        if chat.chat_type != ChatType.GROUP:
            raise ValueError("Cannot add members to direct chats")

        # Check if already member
        existing_query = select(ChatMember).where(
            and_(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == new_member_id
            )
        )
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ValueError("User is already a member")

        # Add member
        member = ChatMember(
            chat_id=chat_id,
            user_id=new_member_id,
            role=ChatMemberRole.MEMBER
        )
        self.db.add(member)

        # Get user for system message
        user_query = select(User).where(User.id == new_member_id)
        user_result = await self.db.execute(user_query)
        new_user = user_result.scalar_one_or_none()

        # Create system message
        if new_user:
            system_msg = Message(
                chat_id=chat_id,
                content=f"{new_user.first_name} {new_user.last_name or ''} приєднався до чату".strip(),
                is_system=True
            )
            self.db.add(system_msg)

        await self.db.commit()
        return member

    async def remove_member(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        member_id: uuid.UUID
    ) -> bool:
        """Видалити учасника з групового чату"""
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            raise ValueError("Chat not found or access denied")

        if chat.chat_type != ChatType.GROUP:
            raise ValueError("Cannot remove members from direct chats")

        # Find member
        member_query = select(ChatMember).where(
            and_(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == member_id
            )
        ).options(selectinload(ChatMember.user))

        member_result = await self.db.execute(member_query)
        member = member_result.scalar_one_or_none()

        if not member:
            raise ValueError("Member not found")

        # Create system message
        if member.user:
            system_msg = Message(
                chat_id=chat_id,
                content=f"{member.user.first_name} {member.user.last_name or ''} покинув чат".strip(),
                is_system=True
            )
            self.db.add(system_msg)

        await self.db.delete(member)
        await self.db.commit()

        return True

    async def mark_as_read(
        self,
        chat_id: uuid.UUID,
        user_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> bool:
        """Позначити повідомлення як прочитане"""
        member_query = select(ChatMember).where(
            and_(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id
            )
        )

        result = await self.db.execute(member_query)
        member = result.scalar_one_or_none()

        if not member:
            raise ValueError("Not a member of this chat")

        member.last_read_message_id = message_id
        await self.db.commit()

        return True

    async def get_unread_count(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Отримати кількість непрочитаних повідомлень"""
        member_query = select(ChatMember).where(
            and_(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id
            )
        )

        result = await self.db.execute(member_query)
        member = result.scalar_one_or_none()

        if not member:
            return 0

        if not member.last_read_message_id:
            # All messages are unread
            count_query = select(func.count(Message.id)).where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id
                )
            )
        else:
            # Count messages after last read
            last_read_query = select(Message.created_at).where(
                Message.id == member.last_read_message_id
            )
            last_read_result = await self.db.execute(last_read_query)
            last_read_time = last_read_result.scalar_one_or_none()

            if not last_read_time:
                return 0

            count_query = select(func.count(Message.id)).where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                    Message.created_at > last_read_time
                )
            )

        count_result = await self.db.execute(count_query)
        return count_result.scalar() or 0
