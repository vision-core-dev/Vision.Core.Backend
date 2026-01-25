"""
WebSocket для real-time чату.
Підключення: ws://localhost:8000/api/v1/Hub/ws/chat
"""

import uuid
import json
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.Infrastructure.Database import async_session
from app.Services.Hub.ChatService import ChatService

chat_ws_router = APIRouter()


class ChatConnectionManager:
    """Manages WebSocket connections for chat"""
    
    def __init__(self):
        # user_id -> set of websockets (user can have multiple tabs/devices)
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> user_id mapping for quick lookup
        self.ws_to_user: Dict[WebSocket, str] = {}
        # chat_id -> set of user_ids (for broadcasting to chat members)
        self.chat_members: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's websocket"""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        
        self.user_connections[user_id].add(websocket)
        self.ws_to_user[websocket] = user_id
        
        print(f"✅ [Chat WS] User {user_id} connected. Total users: {len(self.user_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a user's websocket"""
        user_id = self.ws_to_user.get(websocket)
        if not user_id:
            return
        
        # Remove websocket from user's connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            
            # If user has no more connections, remove them completely
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # Remove from all chat member lists
                for chat_id in list(self.chat_members.keys()):
                    self.chat_members[chat_id].discard(user_id)
        
        # Remove from ws_to_user mapping
        if websocket in self.ws_to_user:
            del self.ws_to_user[websocket]
        
        print(f"❌ [Chat WS] User {user_id} disconnected. Total users: {len(self.user_connections)}")
    
    def register_user_to_chat(self, user_id: str, chat_id: str):
        """Register a user as member of a chat for broadcasting"""
        if chat_id not in self.chat_members:
            self.chat_members[chat_id] = set()
        self.chat_members[chat_id].add(user_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user (all their connections)"""
        if user_id not in self.user_connections:
            return
        
        disconnected = []
        for ws in self.user_connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[Chat WS] Error sending to user {user_id}: {e}")
                disconnected.append(ws)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_to_chat(self, chat_id: str, message: dict, exclude_user_id: str = None):
        """Broadcast a message to all members of a chat"""
        if chat_id not in self.chat_members:
            return
        
        for user_id in self.chat_members[chat_id]:
            if user_id != exclude_user_id:
                await self.send_to_user(user_id, message)
    
    async def broadcast_typing(self, chat_id: str, user_id: str, user_name: str, is_typing: bool):
        """Broadcast typing indicator to chat members"""
        message = {
            "type": "typing",
            "chat_id": chat_id,
            "user_id": user_id,
            "user_name": user_name,
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_chat(chat_id, message, exclude_user_id=user_id)
    
    async def broadcast_new_message(self, chat_id: str, message_data: dict, sender_id: str = None):
        """Broadcast new message to chat members"""
        message = {
            "type": "new_message",
            "chat_id": chat_id,
            "message": message_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_chat(chat_id, message, exclude_user_id=sender_id)
    
    async def broadcast_message_read(self, chat_id: str, user_id: str, message_id: str):
        """Broadcast message read status to chat members"""
        message = {
            "type": "message_read",
            "chat_id": chat_id,
            "user_id": user_id,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast_to_chat(chat_id, message, exclude_user_id=user_id)


# Global chat connection manager
chat_manager = ChatConnectionManager()


# Export for use in REST API (to broadcast on message send)
def get_chat_manager() -> ChatConnectionManager:
    return chat_manager


@chat_ws_router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Client connects and sends:
    - {"type": "identify", "user_id": "uuid"} - to identify the user
    - {"type": "join_chat", "chat_id": "uuid"} - to join a chat room
    - {"type": "typing_start", "chat_id": "uuid"} - typing indicator start
    - {"type": "typing_stop", "chat_id": "uuid"} - typing indicator stop
    - {"type": "mark_read", "chat_id": "uuid", "message_id": "uuid"} - mark message as read
    - {"type": "ping"} - keepalive
    
    Server sends:
    - {"type": "connected", "user_id": "uuid"} - connection confirmed
    - {"type": "new_message", "chat_id": "uuid", "message": {...}} - new message
    - {"type": "typing", "chat_id": "uuid", "user_id": "uuid", "is_typing": bool} - typing indicator
    - {"type": "message_read", "chat_id": "uuid", "user_id": "uuid", "message_id": "uuid"} - message read
    - {"type": "pong"} - keepalive response
    """
    
    user_id = None
    user_name = "Користувач"
    
    try:
        # Accept connection first
        await websocket.accept()
        
        # Wait for user identification
        try:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "identify":
                user_id = message.get("user_id")
                user_name = message.get("user_name", "Користувач")
                
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "user_id required"})
                    await websocket.close()
                    return
                
                # Register connection
                if user_id not in chat_manager.user_connections:
                    chat_manager.user_connections[user_id] = set()
                
                chat_manager.user_connections[user_id].add(websocket)
                chat_manager.ws_to_user[websocket] = user_id
                
                print(f"✅ [Chat WS] User {user_id} ({user_name}) identified and connected")
                
                # Load user's chats and register them - use temporary session
                async with async_session() as db:
                    service = ChatService(db)
                    try:
                        user_chats = await service.get_user_chats(uuid.UUID(user_id))
                        for chat in user_chats:
                            chat_manager.register_user_to_chat(user_id, str(chat.id))
                    except Exception as e:
                        print(f"[Chat WS] Error loading user chats: {e}")
                
                # Send confirmation
                await websocket.send_json({
                    "type": "connected",
                    "user_id": user_id,
                    "message": "Successfully connected to chat"
                })
                
        except WebSocketDisconnect:
            return
        except Exception as e:
            print(f"[Chat WS] Error during identification: {e}")
            return
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                msg_type = message.get("type")
                
                # Handle different message types
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "join_chat":
                    chat_id = message.get("chat_id")
                    if chat_id:
                        chat_manager.register_user_to_chat(user_id, chat_id)
                        await websocket.send_json({
                            "type": "joined_chat",
                            "chat_id": chat_id
                        })
                
                elif msg_type == "typing_start":
                    chat_id = message.get("chat_id")
                    if chat_id:
                        await chat_manager.broadcast_typing(chat_id, user_id, user_name, True)
                
                elif msg_type == "typing_stop":
                    chat_id = message.get("chat_id")
                    if chat_id:
                        await chat_manager.broadcast_typing(chat_id, user_id, user_name, False)
                
                elif msg_type == "mark_read":
                    chat_id = message.get("chat_id")
                    message_id = message.get("message_id")
                    if chat_id and message_id:
                        # Update in database - use temporary session
                        try:
                            async with async_session() as db:
                                service = ChatService(db)
                                await service.mark_as_read(
                                    uuid.UUID(chat_id),
                                    uuid.UUID(user_id),
                                    uuid.UUID(message_id)
                                )
                            # Broadcast to other members
                            await chat_manager.broadcast_message_read(chat_id, user_id, message_id)
                        except Exception as e:
                            print(f"[Chat WS] Error marking as read: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": str(e)
                            })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                print(f"[Chat WS] Error in websocket loop: {e}")
                break
                
    finally:
        if user_id:
            chat_manager.disconnect(websocket)
