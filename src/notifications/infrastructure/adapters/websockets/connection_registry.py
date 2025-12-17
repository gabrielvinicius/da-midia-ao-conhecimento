# src/notifications/infrastructure/connection_registry.py
from typing import Dict, List

from fastapi import WebSocket


class WebSocketConnectionRegistry:
    """Manage active WebSocket connections by user ID."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    def add(self, user_id: str, websocket: WebSocket):
        """Adds a new WebSocket connection for a user."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def remove(self, user_id: str, websocket: WebSocket):
        """Removes a WebSocket connection for a user."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            # If the user has no more connections, remove their entry
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def get_connections(self, user_id: str) -> List[WebSocket]:
        """Retrieves all active connections for a specific user."""
        return self.active_connections.get(user_id, [])

    def get_all_connections(self) -> List[WebSocket]:
        """Returns a list of all active WebSocket connections across all users."""
        all_sockets = []
        for user_connections in self.active_connections.values():
            all_sockets.extend(user_connections)
        return all_sockets
