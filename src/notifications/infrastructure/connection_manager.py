# src/notifications/infrastructure/connection_manager.py
from fastapi import WebSocket

from .connection_registry import WebSocketConnectionRegistry
from .websocket_logger import WebSocketLogger


class ConnectionManager:
    """
    Orchestrates WebSocket connections and logging.
    Acts as a facade, delegating connection storage to a registry and logging to a logger.
    """
    def __init__(self, registry: WebSocketConnectionRegistry, logger: WebSocketLogger):
        self.registry = registry
        self.logger = logger

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accepts and registers a new WebSocket connection, then logs the event."""
        await websocket.accept()
        self.registry.add(user_id, websocket)
        total = len(self.registry.get_connections(user_id))
        self.logger.log_connect(user_id, total)

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Removes a WebSocket connection and logs the event."""
        self.registry.remove(user_id, websocket)
        remaining = len(self.registry.get_connections(user_id))
        self.logger.log_disconnect(user_id, remaining)

    async def send_personal_message(self, message: str, user_id: str):
        """Sends a message to all connections of a specific user."""
        connections = self.registry.get_connections(user_id)
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.log_error(user_id, e, "Failed to send personal message")
                # Optionally, handle dead connections here
                self.disconnect(user_id, connection)

    async def broadcast(self, message: str):
        """Sends a message to all active connections."""
        all_connections = self.registry.get_all_connections()
        for connection in all_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                # Need a way to map connection back to user_id if we want to log this better
                self.logger.log_error("broadcast", e, "Failed to broadcast message")


# --- Singleton Instance ---
# Create a single, globally accessible instance of the ConnectionManager,
# injecting its dependencies.
registry_instance = WebSocketConnectionRegistry()
logger_instance = WebSocketLogger()
manager = ConnectionManager(registry=registry_instance, logger=logger_instance)