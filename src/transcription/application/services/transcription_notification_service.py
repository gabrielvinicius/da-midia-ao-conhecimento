# src/transcription/application/services/transcription_notification_service.py
"""
Transcription Notification Service following SRP principle.
Responsible only for transcription-related notifications.
"""
import structlog
from typing import Optional

from src.transcription.domain.interfaces import NotificationService
from src.transcription.domain.transcription import Transcription
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class TranscriptionNotificationService(NotificationService):
    """
    Handles all transcription-related notifications.
    Follows SRP: Only responsible for transcription notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_transcription_started(self, user_id: str, media_id: str):
        """Notify user that transcription has started."""
        try:
            message = {
                "type": "transcription_started",
                "media_id": media_id,
                "message": "Transcription processing started"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "transcription.notification.started_sent",
                user_id=user_id,
                media_id=media_id
            )
        except Exception as e:
            logger.warning(
                "transcription.notification.started_failed",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
    
    async def notify_transcription_completed(
        self, 
        user_id: str, 
        media_id: str, 
        transcription: Transcription
    ):
        """Notify user that transcription has completed."""
        try:
            message = {
                "type": "transcription_completed",
                "media_id": media_id,
                "transcription_id": str(transcription.id),
                "text_length": len(transcription.text),
                "message": "Transcription completed successfully"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "transcription.notification.completed_sent",
                user_id=user_id,
                media_id=media_id,
                transcription_id=str(transcription.id)
            )
        except Exception as e:
            logger.warning(
                "transcription.notification.completed_failed",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
    
    async def notify_transcription_failed(
        self, 
        user_id: str, 
        media_id: str, 
        error: str
    ):
        """Notify user that transcription has failed."""
        try:
            message = {
                "type": "transcription_failed",
                "media_id": media_id,
                "error": error,
                "message": f"Transcription failed: {error}"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "transcription.notification.failed_sent",
                user_id=user_id,
                media_id=media_id,
                error=error
            )
        except Exception as e:
            logger.warning(
                "transcription.notification.failed_send_error",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )