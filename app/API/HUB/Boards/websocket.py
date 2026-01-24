import uuid
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb

board_ws_router = APIRouter()


class BoardConnectionManager:
    """Manages WebSocket connections for board updates"""
    
    def __init__(self):
        # board_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # board_id -> dict of {websocket: user_info}
        self.user_presence: Dict[str, Dict[WebSocket, dict]] = {}
    
    async def connect(self, websocket: WebSocket, board_id: str, user_info: dict = None):
        """Connect a client to a specific board"""
        await websocket.accept()
        if board_id not in self.active_connections:
            self.active_connections[board_id] = set()
            self.user_presence[board_id] = {}
        
        self.active_connections[board_id].add(websocket)
        if user_info:
            self.user_presence[board_id][websocket] = user_info
        
        print(f"✅ Client connected to board {board_id}. Total connections: {len(self.active_connections[board_id])}")
        
        # Broadcast updated user list to all clients
        await self.broadcast_user_list(board_id)
    
    def disconnect(self, websocket: WebSocket, board_id: str):
        """Disconnect a client from a board"""
        if board_id in self.active_connections:
            self.active_connections[board_id].discard(websocket)
            if websocket in self.user_presence.get(board_id, {}):
                del self.user_presence[board_id][websocket]
            
            if not self.active_connections[board_id]:
                del self.active_connections[board_id]
                if board_id in self.user_presence:
                    del self.user_presence[board_id]
        
        print(f"❌ Client disconnected from board {board_id}")
    
    def get_active_users(self, board_id: str) -> list:
        """Get list of active users on a board"""
        if board_id not in self.user_presence:
            return []
        
        users = []
        seen_user_ids = set()
        for user_info in self.user_presence[board_id].values():
            user_id = user_info.get('user_id')
            if user_id and user_id not in seen_user_ids:
                users.append(user_info)
                seen_user_ids.add(user_id)
        
        return users
    
    async def broadcast_user_list(self, board_id: str):
        """Broadcast the current list of active users to all clients"""
        active_users = self.get_active_users(board_id)
        await self.broadcast_to_board(board_id, {
            "type": "user_presence",
            "users": active_users,
            "count": len(active_users)
        })
    
    async def broadcast_to_board(self, board_id: str, message: dict, exclude: WebSocket = None):
        """Send a message to all clients connected to a specific board"""
        if board_id not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[board_id]:
            if connection == exclude:
                continue
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, board_id)


# Global connection manager
manager = BoardConnectionManager()



@board_ws_router.websocket("/{board_id}/ws")
async def board_websocket(
    websocket: WebSocket,
    board_id: uuid.UUID,
    db: AsyncSession = Depends(getdb)
):
    """
    WebSocket endpoint for real-time board updates.
    
    Messages format:
    - Client -> Server: {"type": "ping"} or {"type": "user_identify", "user": {...}}
    - Server -> Client: {"type": "board_update", "data": {...}} or {"type": "user_presence", "users": [...]}
    """
    board_id_str = str(board_id)
    user_info = None
    
    # Accept connection without user info initially
    await manager.connect(websocket, board_id_str)
    
    try:
        # Send initial connection confirmation
        try:
            await websocket.send_json({
                "type": "connected",
                "board_id": board_id_str,
                "message": "Connected to board updates. Please send user_identify message."
            })
        except Exception as e:
            print(f"Error sending initial data: {e}")
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.get("type") == "user_identify":
                    # Client identifies themselves
                    user_info = message.get("user", {})
                    # Update connection with user info
                    if board_id_str in manager.user_presence:
                        manager.user_presence[board_id_str][websocket] = user_info
                    # Broadcast updated user list
                    await manager.broadcast_user_list(board_id_str)
                    await websocket.send_json({
                        "type": "identified",
                        "message": "User identified successfully"
                    })
                
                elif message.get("type") == "request_update":
                    # Client requests board update
                    await websocket.send_json({
                        "type": "update_requested",
                        "message": "Update will be sent when available"
                    })
                
                elif message.get("type") == "board_changed":
                    # Broadcast to all other clients that board has changed
                    await manager.broadcast_to_board(
                        board_id_str,
                        {
                            "type": "board_update",
                            "action": message.get("action", "update"),
                            "timestamp": message.get("timestamp")
                        },
                        exclude=websocket
                    )
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                print(f"Error in websocket loop: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})
                
    finally:
        manager.disconnect(websocket, board_id_str)
        # Broadcast updated user list after disconnect
        if board_id_str in manager.active_connections:
            await manager.broadcast_user_list(board_id_str)



async def notify_board_update(board_id: uuid.UUID, action: str = "update", data: dict = None):
    """
    Helper function to notify all connected clients about board updates.
    Call this function after any board modification (task move, create, update, etc.)
    """
    board_id_str = str(board_id)
    message = {
        "type": "board_update",
        "action": action,
        "data": data or {}
    }
    await manager.broadcast_to_board(board_id_str, message)
