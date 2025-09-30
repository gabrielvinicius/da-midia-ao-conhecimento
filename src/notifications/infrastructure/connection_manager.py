from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    """Manages active WebSocket connections for real-time notifications."""

    def __init__(self):
        # Stores active connections, mapping user IDs to a list of their WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accepts a new WebSocket connection for a given user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"New connection for user {user_id}. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Removes a WebSocket connection for a given user."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            print(f"Disconnected user {user_id}. Remaining connections: {len(self.active_connections.get(user_id, []))}")

    async def send_personal_message(self, message: str, user_id: str):
        """Sends a message to all active WebSocket connections for a specific user."""
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            for connection in connections:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        """Sends a message to all active WebSocket connections."""
        for user_id in self.active_connections:
            await self.send_personal_message(message, user_id)

# Create a single, globally accessible instance of the ConnectionManager
manager = ConnectionManager()
