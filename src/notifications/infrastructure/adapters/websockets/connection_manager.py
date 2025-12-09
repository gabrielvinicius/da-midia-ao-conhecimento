from typing import Dict, List
from uuid import UUID
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # Dictionary to store connections: {user_id: [list of websockets]}
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if len(self.active_connections[user_id]) == 0:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # If there's an error sending to a connection, remove it
                    self.disconnect(user_id, connection)

    async def send_to_user(self, user_id: UUID, message: dict):
        """Send a message to a specific user. Returns True if successful."""
        user_id_str = str(user_id)
        if user_id_str in self.active_connections:
            success = True
            for connection in self.active_connections[user_id_str]:
                try:
                    await connection.send_json(message)
                except:
                    # If there's an error sending to a connection, remove it
                    self.disconnect(user_id_str, connection)
                    success = False
            return success
        return False

    async def broadcast(self, message: str):
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


# Create a global instance of the manager
manager = ConnectionManager()