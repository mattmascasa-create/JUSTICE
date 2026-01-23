"""
WebSocket connection manager for real-time features
"""
from typing import Dict, List
from fastapi import WebSocket
import json
import asyncio


class ConnectionManager:
    """Manages WebSocket connections for real-time features"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.encounter_viewers: Dict[str, List[WebSocket]] = {}
        self.share_viewers: Dict[str, List[WebSocket]] = {}  # For shared encounter viewers
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(conn, user_id)
    
    async def broadcast(self, message: dict):
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    async def handle_ping(self, websocket: WebSocket, data: dict):
        """Handle ping message and respond with pong"""
        try:
            await websocket.send_json({
                "type": "pong",
                "timestamp": data.get("timestamp"),
                "server_time": asyncio.get_event_loop().time()
            })
        except Exception:
            pass
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user"""
        return len(self.active_connections.get(user_id, []))
    
    # Encounter streaming methods
    async def add_viewer(self, encounter_id: str, websocket: WebSocket):
        await websocket.accept()
        if encounter_id not in self.encounter_viewers:
            self.encounter_viewers[encounter_id] = []
        self.encounter_viewers[encounter_id].append(websocket)
    
    def remove_viewer(self, encounter_id: str, websocket: WebSocket):
        if encounter_id in self.encounter_viewers:
            if websocket in self.encounter_viewers[encounter_id]:
                self.encounter_viewers[encounter_id].remove(websocket)
            if not self.encounter_viewers[encounter_id]:
                del self.encounter_viewers[encounter_id]
    
    async def broadcast_to_viewers(self, encounter_id: str, data: bytes):
        if encounter_id in self.encounter_viewers:
            for viewer in self.encounter_viewers[encounter_id]:
                try:
                    await viewer.send_bytes(data)
                except:
                    pass
    
    def get_viewer_count(self, encounter_id: str) -> int:
        return len(self.encounter_viewers.get(encounter_id, []))
    
    # Shared encounter viewer methods
    async def add_share_viewer(self, encounter_id: str, websocket: WebSocket):
        """Add a viewer to a shared encounter"""
        await websocket.accept()
        if encounter_id not in self.share_viewers:
            self.share_viewers[encounter_id] = []
        self.share_viewers[encounter_id].append(websocket)
    
    def remove_share_viewer(self, encounter_id: str, websocket: WebSocket):
        """Remove a viewer from a shared encounter"""
        if encounter_id in self.share_viewers:
            if websocket in self.share_viewers[encounter_id]:
                self.share_viewers[encounter_id].remove(websocket)
            if not self.share_viewers[encounter_id]:
                del self.share_viewers[encounter_id]
    
    async def broadcast_to_share_viewers(self, encounter_id: str, message: dict):
        """Send a message to all viewers of a shared encounter"""
        if encounter_id in self.share_viewers:
            for viewer in self.share_viewers[encounter_id][:]:  # Copy list to avoid mutation during iteration
                try:
                    await viewer.send_json(message)
                except:
                    self.remove_share_viewer(encounter_id, viewer)
    
    def get_share_viewer_count(self, encounter_id: str) -> int:
        """Get the number of viewers for a shared encounter"""
        return len(self.share_viewers.get(encounter_id, []))


# Global manager instance
manager = ConnectionManager()
