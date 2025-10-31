# src/video_processing/application/video_processing_service.py
"""
Consolidated Video Processing Service.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
import time

from src.video_processing.infrastructure.video_audio_extractor import FFmpegVideoAudioExtractor
from src.video_processing.infrastructure.video_thumbnail_generator import FFmpegVideoThumbnailGenerator
from src.video_processing.infrastructure.task_scheduler import CeleryVideoProcessingTaskScheduler
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
# TODO: Adicionar logger e metrics específicos para video_processing

logger = structlog.get_logger(__name__)


class VideoProcessingService:
    """
    Consolidated service for all video processing operations.
    """
    
    def __init__(
        self,
        video_audio_extractor: FFmpegVideoAudioExtractor,
        video_thumbnail_generator: FFmpegVideoThumbnailGenerator,
        video_processing_task_scheduler: CeleryVideoProcessingTaskScheduler,
        storage_service: S3StorageService,
        # TODO: Adicionar video_processing_logger, video_processing_metrics
    ):
        self.audio_extractor = video_audio_extractor
        self.thumbnail_generator = video_thumbnail_generator
        self.task_scheduler = video_processing_task_scheduler
        self.storage = storage_service
        # self.logger = video_processing_logger # Placeholder
        # self.metrics = video_processing_metrics # Placeholder

    async def request_video_processing(self, media_id: UUID, file_path: str, storage_provider: str) -> Dict[str, Any]:
        """Requests the processing of a video for a given media item by scheduling a task."""
        logger.info("video_processing.request.started", media_id=str(media_id), file_path=file_path)
        try:
            task_result = await self.task_scheduler.schedule_process_video_task(
                media_id=str(media_id),
                file_path=file_path
            )
            
            logger.info("video_processing.request.completed", media_id=str(media_id), task_id=task_result.get("task_id"))
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Video processing task scheduled successfully"
            }
        except Exception as e:
            logger.error("video_processing.request.failed", media_id=str(media_id), error=str(e))
            raise
