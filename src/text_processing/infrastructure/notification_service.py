# src/text_processing/infrastructure/notification_service.py
"""
Text processing notification service implementation - SRP compliance.
"""
import json
import structlog
from typing import Optional

from src.text_processing.domain.interfaces import TextNotificationService
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class WebSocketTextNotificationService(TextNotificationService):
    """
    WebSocket-based notification service for text processing operations.
    Follows SRP - only responsible for notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_started(self, media_id: str, user_id: str) -> None:
        """Notify text processing started."""
        await self._send_notification(
            user_id=user_id,
            notification_type="text_processing_started",
            media_id=media_id,
            message="Text processing started"
        )
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        text_length: int
    ) -> None:
        """Notify text processing completed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="text_processing_completed",
            media_id=media_id,
            message=f"Text processing completed. Extracted {text_length} characters.",
            payload={"text_length": text_length}
        )
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify text processing failed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="text_processing_failed",
            media_id=media_id,
            message=f"Text processing failed: {error}",
            payload={"error": error}
        )
    
    async def _send_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        media_id: str,
        message: str,
        payload: Optional[dict] = None
    ) -> None:
        """Send notification via WebSocket."""
        try:
            notification_payload = {
                "type": notification_type,
                "entity": "text_processing",
                "message": message,
                "payload": {
                    "media_id": media_id,
                    **(payload or {})
                }
            }
            
            await self._connection_manager.send_personal_message(
                json.dumps(notification_payload), 
                user_id
            )
            
            logger.info(
                "text_processing.notification.sent",
                type=notification_type,
                media_id=media_id,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(
                "text_processing.notification.failed",
                type=notification_type,
                media_id=media_id,
                user_id=user_id,
                error=str(e)
            )


class EmailTextNotificationService(TextNotificationService):
    """
    Email-based notification service for text processing operations.
    Alternative implementation following same interface.
    """
    
    def __init__(self, email_service):
        self._email_service = email_service
    
    async def notify_started(self, media_id: str, user_id: str) -> None:
        """Notify text processing started via email."""
        # Implementation would send email
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        text_length: int
    ) -> None:
        """Notify text processing completed via email."""
        # Implementation would send email with results
        pass
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify text processing failed via email."""
        # Implementation would send error email
        pass


class NoOpTextNotificationService(TextNotificationService):
    """
    No-operation notification service for testing.
    Follows Null Object pattern.
    """
    
    async def notify_started(self, media_id: str, user_id: str) -> None:
        """No-op implementation."""
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        text_length: int
    ) -> None:
        """No-op implementation."""
        pass
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """No-op implementation."""
        pass