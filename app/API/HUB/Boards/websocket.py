import uuid
import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb

board_ws_router = APIRouter(prefix="/Boards")


class BoardConnectionManager:
    """Manages WebSocket connections for board updates"""
    
    def __init__(self):
        # board_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, board_id: str):
        """Connect a client to a specific board"""
        await websocket.accept()
        if board_id not in self.active_connections:
            self.active_connections[board_id] = set()
        self.active_connections[board_id].add(websocket)
        print(f"✅ Client connected to board {board_id}. Total connections: {len(self.active_connections[board_id])}")
    
    def disconnect(self, websocket: WebSocket, board_id: str):
        """Disconnect a client from a board"""
        if board_id in self.active_connections:
            self.active_connections[board_id].discard(websocket)
            if not self.active_connections[board_id]:
                del self.active_connections[board_id]
        print(f"❌ Client disconnected from board {board_id}")
    
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
    - Client -> Server: {"type": "ping"} or {"type": "update", "data": {...}}
    - Server -> Client: {"type": "board_update", "data": {...}}
    """
    board_id_str = str(board_id)
    
    # Accept connection
    await manager.connect(websocket, board_id_str)
    
    try:
        # Send initial board data
        try:
            # Note: We can't use getuser_ws here as it requires authentication
            # For now, we'll send a connection confirmation
            await websocket.send_json({
                "type": "connected",
                "board_id": board_id_str,
                "message": "Connected to board updates"
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
                
                elif message.get("type") == "request_update":
                    # Client requests board update
                    # In a real scenario, you'd fetch and send board data here
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
