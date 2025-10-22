# src/video_processing/application/video_processing_service.py
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.video_processing.domain.interfaces import (
    IVideoAudioExtractor,
    IVideoThumbnailGenerator,
    IVideoProcessingTaskScheduler,
    # TODO: Adicionar VideoProcessingOperationLogger, VideoProcessingMetrics
)
# TODO: Adicionar entidade Video (se existir)

logger = structlog.get_logger(__name__)


class VideoProcessingService:
    """Application service for orchestrating video processing operations."""

    def __init__(
        self,
        video_audio_extractor: IVideoAudioExtractor,
        video_thumbnail_generator: IVideoThumbnailGenerator,
        video_processing_task_scheduler: IVideoProcessingTaskScheduler,
        # TODO: Adicionar video_processing_logger, video_processing_metrics
    ):
        self.video_audio_extractor = video_audio_extractor
        self.video_thumbnail_generator = video_thumbnail_generator
        self.video_processing_task_scheduler = video_processing_task_scheduler
        # self.video_processing_logger = video_processing_logger # Placeholder
        # self.video_processing_metrics = video_processing_metrics # Placeholder

    async def request_video_processing(self, media_id: UUID, file_path: str, storage_provider: str) -> Dict[str, Any]:
        """Requests the processing of a video for a given media item."""
        logger.info(
            "video_processing_service.request_video_processing",
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider
        )
        try:
            # TODO: Criar entidade Video em PENDING state e persistir
            # Por enquanto, vamos agendar a tarefa diretamente

            task_result = await self.video_processing_task_scheduler.schedule_process_video_task(
                media_id=str(media_id),
                file_path=file_path
            )

            logger.info(
                "video_processing_service.video_processing_scheduled",
                media_id=str(media_id),
                task_id=task_result.get("task_id")
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Video processing task scheduled successfully"
            }
        except Exception as e:
            logger.error(
                "video_processing_service.request_video_processing_failed",
                media_id=str(media_id),
                error=str(e)
            )
            raise

    # TODO: Adicionar outros métodos de serviço conforme necessário
    # Ex: get_video_processing_status, get_video_metadata, etc.
