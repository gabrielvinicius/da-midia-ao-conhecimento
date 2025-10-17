# src/summarization/infrastructure/notification_service.py
"""
Summarization notification service implementation - SRP compliance.
"""
import json
import structlog
from typing import Optional

from src.summarization.domain.interfaces import SummaryNotificationService
from src.summarization.domain.summary import Summary
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class WebSocketSummaryNotificationService(SummaryNotificationService):
    """
    WebSocket-based notification service for summarization operations.
    Follows SRP - only responsible for notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_started(self, summary: Summary, user_id: str) -> None:
        """Notify summarization started."""
        await self._send_notification(
            user_id=user_id,
            notification_type="summarization_started",
            summary=summary,
            message="Summarization process started"
        )
    
    async def notify_completed(self, summary: Summary, user_id: str) -> None:
        """Notify summarization completed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="summarization_completed",
            summary=summary,
            message="Summarization completed successfully"
        )
    
    async def notify_failed(self, summary: Summary, user_id: str, error: str) -> None:
        """Notify summarization failed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="summarization_failed",
            summary=summary,
            message=f"Summarization failed: {error}",
            error=error
        )
    
    async def _send_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        summary: Summary,
        message: str,
        error: Optional[str] = None
    ) -> None:
        """Send notification via WebSocket."""
        try:
            payload = {
                "type": notification_type,
                "entity": "summary",
                "message": message,
                "payload": {
                    "id": str(summary.id),
                    "media_id": str(summary.media_id),
                    "status": summary.status.value,
                    "provider": summary.provider,
                    "created_at": summary.created_at.isoformat() if summary.created_at else None,
                    "processed_at": summary.processed_at.isoformat() if summary.processed_at else None
                }
            }
            
            if error:
                payload["payload"]["error_message"] = error
            
            if summary.text and summary.status.value == "COMPLETED":
                payload["payload"]["text"] = summary.text
            
            await self._connection_manager.send_personal_message(
                json.dumps(payload), 
                user_id
            )
            
            logger.info(
                "summarization.notification.sent",
                type=notification_type,
                summary_id=str(summary.id),
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(
                "summarization.notification.failed",
                type=notification_type,
                summary_id=str(summary.id),
                user_id=user_id,
                error=str(e)
            )


class EmailSummaryNotificationService(SummaryNotificationService):
    """
    Email-based notification service for summarization operations.
    Alternative implementation following same interface.
    """
    
    def __init__(self, email_service):
        self._email_service = email_service
    
    async def notify_started(self, summary: Summary, user_id: str) -> None:
        """Notify summarization started via email."""
        # Implementation would send email
        pass
    
    async def notify_completed(self, summary: Summary, user_id: str) -> None:
        """Notify summarization completed via email."""
        # Implementation would send email with summary
        pass
    
    async def notify_failed(self, summary: Summary, user_id: str, error: str) -> None:
        """Notify summarization failed via email."""
        # Implementation would send error email
        pass


class NoOpSummaryNotificationService(SummaryNotificationService):
    """
    No-operation notification service for testing.
    Follows Null Object pattern.
    """
    
    async def notify_started(self, summary: Summary, user_id: str) -> None:
        """No-op implementation."""
        pass
    
    async def notify_completed(self, summary: Summary, user_id: str) -> None:
        """No-op implementation."""
        pass
    
    async def notify_failed(self, summary: Summary, user_id: str, error: str) -> None:
        """No-op implementation."""
        pass