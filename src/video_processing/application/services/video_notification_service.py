# src/video_processing/application/services/video_notification_service.py
"""
Video Notification Service following SRP principle.
Responsible only for video processing-related notifications.
"""
import structlog
from typing import Dict, Any

from src.video_processing.domain.interfaces import VideoNotificationService
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class DefaultVideoNotificationService(VideoNotificationService):
    """
    Handles all video processing-related notifications.
    Follows SRP: Only responsible for video processing notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_video_processing_started(self, user_id: str, media_id: str):
        """Notify user that video processing has started."""
        try:
            message = {
                "type": "video_processing_started",
                "media_id": media_id,
                "message": "Video processing started"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "video.notification.started_sent",
                user_id=user_id,
                media_id=media_id
            )
        except Exception as e:
            logger.warning(
                "video.notification.started_failed",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
    
    async def notify_video_processing_completed(
        self, 
        user_id: str, 
        media_id: str, 
        result: Dict[str, Any]
    ):
        """Notify user that video processing has completed."""
        try:
            message = {
                "type": "video_processing_completed",
                "media_id": media_id,
                "result": result,
                "message": "Video processing completed successfully"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "video.notification.completed_sent",
                user_id=user_id,
                media_id=media_id
            )
        except Exception as e:
            logger.warning(
                "video.notification.completed_failed",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
    
    async def notify_video_processing_failed(
        self, 
        user_id: str, 
        media_id: str, 
        error: str
    ):
        """Notify user that video processing has failed."""
        try:
            message = {
                "type": "video_processing_failed",
                "media_id": media_id,
                "error": error,
                "message": f"Video processing failed: {error}"
            }
            await self._connection_manager.send_personal_message(user_id, message)
            
            logger.info(
                "video.notification.failed_sent",
                user_id=user_id,
                media_id=media_id,
                error=error
            )
        except Exception as e:
            logger.warning(
                "video.notification.failed_send_error",
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )