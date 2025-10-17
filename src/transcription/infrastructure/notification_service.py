# src/transcription/infrastructure/notification_service.py
"""
Transcription notification service implementation - SRP compliance.
"""
import json
import structlog
from typing import Dict, Any

from src.transcription.domain.interfaces import TranscriptionNotificationService
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class WebSocketTranscriptionNotificationService(TranscriptionNotificationService):
    """
    WebSocket-based notification service for transcription operations.
    Follows SRP - only responsible for notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_started(self, media_id: str, user_id: str, language: str) -> None:
        """Notify transcription started."""
        await self._send_notification(
            user_id=user_id,
            notification_type="transcription_started",
            media_id=media_id,
            message=f"Transcription started for language: {language}",
            payload={"language": language}
        )
    
    async def notify_progress(self, media_id: str, user_id: str, progress: float) -> None:
        """Notify transcription progress."""
        await self._send_notification(
            user_id=user_id,
            notification_type="transcription_progress",
            media_id=media_id,
            message=f"Transcription progress: {progress:.1%}",
            payload={"progress": progress}
        )
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        result: Dict[str, Any]
    ) -> None:
        """Notify transcription completed."""
        text_length = len(result.get("text", ""))
        segments_count = len(result.get("segments", []))
        language = result.get("language", "unknown")
        confidence = result.get("confidence", 0.0)
        
        await self._send_notification(
            user_id=user_id,
            notification_type="transcription_completed",
            media_id=media_id,
            message=f"Transcription completed: {text_length} characters, {segments_count} segments",
            payload={
                "text_length": text_length,
                "segments_count": segments_count,
                "language": language,
                "confidence": confidence
            }
        )
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify transcription failed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="transcription_failed",
            media_id=media_id,
            message=f"Transcription failed: {error}",
            payload={"error": error}
        )
    
    async def _send_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        media_id: str,
        message: str,
        payload: Dict[str, Any] = None
    ) -> None:
        """Send notification via WebSocket."""
        try:
            notification_payload = {
                "type": notification_type,
                "entity": "transcription",
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
                "transcription.notification.sent",
                type=notification_type,
                media_id=media_id,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(
                "transcription.notification.failed",
                type=notification_type,
                media_id=media_id,
                user_id=user_id,
                error=str(e)
            )


class EmailTranscriptionNotificationService(TranscriptionNotificationService):
    """
    Email-based notification service for transcription operations.
    Alternative implementation following same interface.
    """
    
    def __init__(self, email_service):
        self._email_service = email_service
    
    async def notify_started(self, media_id: str, user_id: str, language: str) -> None:
        """Notify transcription started via email."""
        # Implementation would send email
        pass
    
    async def notify_progress(self, media_id: str, user_id: str, progress: float) -> None:
        """Notify transcription progress via email."""
        # Usually not sent via email due to frequency
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        result: Dict[str, Any]
    ) -> None:
        """Notify transcription completed via email."""
        # Implementation would send email with transcription summary
        pass
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify transcription failed via email."""
        # Implementation would send error email
        pass


class NoOpTranscriptionNotificationService(TranscriptionNotificationService):
    """
    No-operation notification service for testing.
    Follows Null Object pattern.
    """
    
    async def notify_started(self, media_id: str, user_id: str, language: str) -> None:
        """No-op implementation."""
        pass
    
    async def notify_progress(self, media_id: str, user_id: str, progress: float) -> None:
        """No-op implementation."""
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        result: Dict[str, Any]
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