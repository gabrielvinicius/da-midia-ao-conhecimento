# src/video_processing/application/services/video_orchestration_service.py
"""
Video Orchestration Service following OCP and DIP principles.
Coordinates video processing workflow without depending on concrete implementations.
"""
import structlog
from typing import Dict, Any
from datetime import datetime

from src.video_processing.domain.interfaces import (
    VideoProcessor,
    VideoOrchestrator,
    VideoNotificationService
)
from src.video_processing.application.services.video_factory import VideoFactory

logger = structlog.get_logger(__name__)


class DefaultVideoOrchestrationService(VideoOrchestrator):
    """
    Orchestrates the complete video processing workflow.
    Follows OCP: Open for extension through processor injection.
    Follows DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        video_processor: VideoProcessor,
        video_factory: VideoFactory,
        notification_service: VideoNotificationService
    ):
        self._processor = video_processor
        self._factory = video_factory
        self._notification_service = notification_service
    
    async def process_video_upload(
        self,
        media_id: str,
        video_data: bytes,
        user_id: str,
        target_format: str = "mp4"
    ) -> Dict[str, Any]:
        """Orchestrate video processing workflow."""
        logger.info(
            "video.orchestration.started",
            media_id=media_id,
            user_id=user_id,
            target_format=target_format
        )
        
        try:
            # Send processing notification
            await self._notification_service.notify_video_processing_started(
                user_id=user_id,
                media_id=media_id
            )
            
            # Validate video
            is_valid = await self._processor.validate_video(video_data)
            if not is_valid:
                raise ValueError("Invalid video format or corrupted data")
            
            # Extract metadata
            metadata = await self._processor.extract_metadata(video_data)
            
            # Process video
            processed_video = await self._processor.process_video(
                video_data=video_data,
                target_format=target_format
            )
            
            # Create result
            result = self._factory.create_processing_result(
                media_id=media_id,
                original_format=metadata.get("format", "unknown"),
                target_format=target_format,
                metadata=metadata
            )
            result["processed_at"] = datetime.utcnow().isoformat()
            result["processed_size"] = len(processed_video)
            
            # Send completion notification
            await self._notification_service.notify_video_processing_completed(
                user_id=user_id,
                media_id=media_id,
                result=result
            )
            
            logger.info(
                "video.orchestration.completed",
                media_id=media_id,
                processed_size=len(processed_video)
            )
            
            return result
            
        except Exception as e:
            # Create error result
            error_result = self._factory.create_error_result(
                media_id=media_id,
                error_message=str(e)
            )
            error_result["processed_at"] = datetime.utcnow().isoformat()
            
            # Send error notification
            await self._notification_service.notify_video_processing_failed(
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
            
            logger.error(
                "video.orchestration.failed",
                media_id=media_id,
                error=str(e)
            )
            
            raise