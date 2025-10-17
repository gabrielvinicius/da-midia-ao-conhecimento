# src/notifications/infrastructure/websocket_logger.py
import logging

# Configure a logger for WebSocket events
logger = logging.getLogger("websocket")


class WebSocketLogger:
    """
    Handles logging for WebSocket connection events.
    This decouples logging from the connection management logic.
    """

    def log_connect(self, user_id: str, total_connections: int):
        """Logs a new client connection."""
        logger.info(f"New connection for user {user_id}. Total connections for user: {total_connections}")

    def log_disconnect(self, user_id: str, remaining_connections: int):
        """Logs a client disconnection."""
        logger.info(f"Disconnected user {user_id}. Remaining connections: {remaining_connections}")

    def log_error(self, user_id: str, error: Exception, message: str = "WebSocket error"):
        """Logs an error related to a WebSocket connection."""
        logger.error(f"{message} for user {user_id}: {error}", exc_info=True)
