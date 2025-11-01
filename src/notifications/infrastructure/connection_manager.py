# src/notifications/infrastructure/connection_manager.py
from fastapi import WebSocket
from typing import Dict, Any, Optional
from uuid import UUID
import json
import structlog


from .connection_registry import WebSocketConnectionRegistry
from .websocket_logger import WebSocketLogger

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Orchestrates WebSocket connections and logging.
    Acts as a facade, delegating connection storage to a registry and logging to a logger.
    """
    def __init__(self, registry: WebSocketConnectionRegistry, logger: WebSocketLogger):
        self.registry = registry
        self.logger = logger

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """
        Accept and register WebSocket connection.
        
        Args:
            user_id: User ID
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.registry.add(str(user_id), websocket)
        total = len(self.registry.get_connections(str(user_id)))
        self.logger.log_connect(str(user_id), total)
        
        logger.info(
            "websocket.connection_established",
            user_id=str(user_id),
            total_connections=total
        )

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        """
        Remove WebSocket connection.
        
        Args:
            user_id: User ID
            websocket: WebSocket connection
        """
        self.registry.remove(str(user_id), websocket)
        remaining = len(self.registry.get_connections(str(user_id)))
        self.logger.log_disconnect(str(user_id), remaining)
        
        logger.info(
            "websocket.connection_closed",
            user_id=str(user_id),
            remaining_connections=remaining
        )

    async def send_to_user(self, user_id: UUID, message: Dict[str, Any]) -> bool:
        """
        Send message to specific user.
        
        Args:
            user_id: Target user ID
            message: Message data
            
        Returns:
            bool: True if message was sent successfully
        """
        connections = self.registry.get_connections(str(user_id))
        if not connections:
            logger.debug(
                "websocket.no_connections",
                user_id=str(user_id)
            )
            return False
        
        success_count = 0
        message_text = json.dumps(message)
        
        for connection in connections[:]:  # Create copy to avoid modification during iteration
            try:
                await connection.send_text(message_text)
                success_count += 1
            except Exception as e:
                self.logger.log_error(str(user_id), e, "Failed to send message to user")
                # Remove dead connection
                self.disconnect(user_id, connection)
        
        success = success_count > 0
        
        logger.debug(
            "websocket.message_sent_to_user",
            user_id=str(user_id),
            success=success,
            connections_tried=len(connections),
            successful_sends=success_count
        )
        
        return success

    async def broadcast(self, message: Dict[str, Any], filter_criteria: Optional[Dict] = None) -> int:
        """
        Broadcast message to all or filtered connections.
        
        Args:
            message: Message data
            filter_criteria: Optional criteria for filtering connections
            
        Returns:
            int: Number of successful sends
        """
        all_connections = self.registry.get_all_connections()
        if not all_connections:
            logger.debug("websocket.no_active_connections_for_broadcast")
            return 0
        
        message_text = json.dumps(message)
        success_count = 0
        
        for connection in all_connections:
            try:
                # TODO: Apply filter_criteria if needed
                await connection.send_text(message_text)
                success_count += 1
            except Exception as e:
                self.logger.log_error("broadcast", e, "Failed to broadcast message")
                # Note: Can't easily remove connection here without user_id mapping
        
        logger.info(
            "websocket.broadcast_completed",
            total_connections=len(all_connections),
            successful_sends=success_count,
            message_type=message.get("type", "unknown")
        )
        
        return success_count

    def get_active_connections(self, user_id: Optional[UUID] = None) -> int:
        """
        Get count of active connections.
        
        Args:
            user_id: Optional user ID for user-specific count
            
        Returns:
            int: Number of active connections
        """
        if user_id:
            return len(self.registry.get_connections(str(user_id)))
        else:
            return len(self.registry.get_all_connections())

    # Legacy methods for backward compatibility
    async def send_personal_message(self, message: str, user_id: str):
        """Legacy method - use send_to_user for new code."""
        try:
            message_dict = {"content": message, "type": "personal"}
            return await self.send_to_user(UUID(user_id), message_dict)
        except ValueError:
            # Handle case where user_id is not a valid UUID
            connections = self.registry.get_connections(user_id)
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    self.logger.log_error(user_id, e, "Failed to send personal message")
                    self.registry.remove(user_id, connection)


# --- Singleton Instance ---
# Create a single, globally accessible instance of the ConnectionManager,
# injecting its dependencies.
registry_instance = WebSocketConnectionRegistry()
logger_instance = WebSocketLogger()
manager = ConnectionManager(registry=registry_instance, logger=logger_instance)
