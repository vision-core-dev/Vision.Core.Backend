"""
WebSocket для відстеження онлайн користувачів на платформі.
Підключення: ws://localhost:8000/api/v1/Hub/ws/online
"""

import uuid
import json
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb

online_ws_router = APIRouter()


class OnlineUsersManager:
    """Manages WebSocket connections for online users tracking"""
    
    def __init__(self):
        # user_id -> set of websockets (user can have multiple tabs/devices)
        self.connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> user_id mapping for quick lookup
        self.ws_to_user: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's websocket"""
        await websocket.accept()
        
        if user_id not in self.connections:
            self.connections[user_id] = set()
        
        self.connections[user_id].add(websocket)
        self.ws_to_user[websocket] = user_id
        
        print(f"✅ User {user_id} connected. Total online users: {len(self.connections)}")
        
        # Broadcast updated online users list to all connected clients
        await self.broadcast_online_users()
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a user's websocket"""
        user_id = self.ws_to_user.get(websocket)
        if not user_id:
            return
        
        # Remove websocket from user's connections
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            
            # If user has no more connections, remove them completely
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        # Remove from ws_to_user mapping
        if websocket in self.ws_to_user:
            del self.ws_to_user[websocket]
        
        print(f"❌ User {user_id} disconnected. Total online users: {len(self.connections)}")
    
    def get_online_user_ids(self) -> list[str]:
        """Get list of all online user IDs"""
        return list(self.connections.keys())
    
    async def broadcast_online_users(self):
        """Broadcast the current list of online users to all connected clients"""
        online_user_ids = self.get_online_user_ids()
        message = {
            "type": "online_users",
            "user_ids": online_user_ids,
            "count": len(online_user_ids),
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected websockets
        disconnected = []
        for user_id, websockets in self.connections.items():
            for ws in websockets:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"Error sending to user {user_id}: {e}")
                    disconnected.append(ws)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user (all their connections)"""
        if user_id not in self.connections:
            return
        
        disconnected = []
        for ws in self.connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")
                disconnected.append(ws)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)


# Global online users manager
online_manager = OnlineUsersManager()


@online_ws_router.websocket("/ws/online")
async def online_users_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(getdb)
):
    """
    WebSocket endpoint for tracking online users.
    
    Client connects and receives:
    - Initial list of online users
    - Real-time updates when users go online/offline
    
    Messages format:
    - Server -> Client: {"type": "online_users", "user_ids": [...], "count": 10}
    - Client -> Server: {"type": "ping"} (keepalive)
    """
    
    # Get user from token (we'll need to implement this)
    # For now, we'll get user_id from query params or initial message
    user_id = None
    
    try:
        # Accept connection first
        await websocket.accept()
        
        # Wait for user identification
        try:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "identify":
                user_id = message.get("user_id")
                if not user_id:
                    await websocket.send_json({"type": "error", "message": "user_id required"})
                    await websocket.close()
                    return
                
                # Register connection
                if user_id not in online_manager.connections:
                    online_manager.connections[user_id] = set()
                
                online_manager.connections[user_id].add(websocket)
                online_manager.ws_to_user[websocket] = user_id
                
                print(f"✅ User {user_id} identified and connected")
                
                # Send confirmation
                await websocket.send_json({
                    "type": "connected",
                    "user_id": user_id,
                    "message": "Successfully connected to online users tracking"
                })
                
                # Broadcast updated online users list
                await online_manager.broadcast_online_users()
                
        except Exception as e:
            print(f"Error during identification: {e}")
            await websocket.close()
            return
        
        # Listen for messages (mainly keepalive pings)
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.get("type") == "get_online":
                    # Client requests current online users
                    online_user_ids = online_manager.get_online_user_ids()
                    await websocket.send_json({
                        "type": "online_users",
                        "user_ids": online_user_ids,
                        "count": len(online_user_ids)
                    })
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                print(f"Error in websocket loop: {e}")
                break
                
    finally:
        if user_id:
            online_manager.disconnect(websocket)
            # Broadcast updated online users list after disconnect
            await online_manager.broadcast_online_users()


# Helper function to check if user is online
def is_user_online(user_id: str) -> bool:
    """Check if a specific user is currently online"""
    return user_id in online_manager.connections


# Helper function to get all online users
def get_online_users() -> list[str]:
    """Get list of all currently online user IDs"""
    return online_manager.get_online_user_ids()
