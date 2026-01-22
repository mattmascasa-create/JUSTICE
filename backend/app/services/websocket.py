"""
WebSocket connection manager for real-time features
"""
from typing import Dict, List
from fastapi import WebSocket
import json


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
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except:
                    pass
    
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


# Global manager instance
manager = ConnectionManager()
