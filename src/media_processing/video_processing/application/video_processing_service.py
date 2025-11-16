# src/video_processing/application/video_processing_service.py
"""Consolidated Video Processing Service."""
import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.video_processing.infrastructure.metrics import (
    PrometheusVideoProcessingMetrics,
)
from src.media_processing.video_processing.infrastructure.task_scheduler import (
    CeleryVideoProcessingTaskScheduler,
)
from src.media_processing.video_processing.infrastructure.video_audio_extractor import (
    FFmpegVideoAudioExtractor,
)
from src.media_processing.video_processing.infrastructure.video_thumbnail_generator import (
    FFmpegVideoThumbnailGenerator,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory

# TODO: Adicionar logger e metrics específicos para video_processing

logger = structlog.get_logger(__name__)


class VideoProcessingService:
    """Consolidated service for all video processing operations."""

    def __init__(
        self,
        video_audio_extractor: FFmpegVideoAudioExtractor,
        video_thumbnail_generator: FFmpegVideoThumbnailGenerator,
        video_processing_task_scheduler: CeleryVideoProcessingTaskScheduler,
        storage_factory: StorageServiceFactory,
        default_storage_provider: str = "local",
        video_processing_metrics: Optional[PrometheusVideoProcessingMetrics] = None,
    ):
        self.audio_extractor = video_audio_extractor
        self.thumbnail_generator = video_thumbnail_generator
        self.task_scheduler = video_processing_task_scheduler
        self._storage_factory = storage_factory
        self._default_storage_provider = default_storage_provider
        self._metrics = video_processing_metrics

    async def request_video_processing(
        self, media_id: UUID, file_path: str, storage_provider: str
    ) -> Dict[str, Any]:
        """Requests the processing of a video for a given media item by scheduling a task."""
        logger.info(
            "video_processing.request.started",
            media_id=str(media_id),
            file_path=file_path,
        )
        try:
            task_result = await self.task_scheduler.schedule_process_video_task(
                media_id=str(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
            )

            logger.info(
                "video_processing.request.completed",
                media_id=str(media_id),
                task_id=task_result.get("task_id"),
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Video processing task scheduled successfully",
            }
        except Exception as exc:
            logger.error(
                "video_processing.request.failed",
                media_id=str(media_id),
                error=str(exc),
            )
            raise

    async def process_video_job(
        self,
        *,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        file_size_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute video processing workflow previously handled inside Celery tasks."""
        start_time = time.monotonic()
        success = False
        provider = storage_provider or self._default_storage_provider
        logger.info(
            "video_processing.job.started",
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=provider,
        )
        try:
            storage_service = self._storage_factory.get_download_service(provider)
            video_data = await storage_service.download_file(file_path)

            audio_result = await self.audio_extractor.extract_audio(
                video_data=video_data,
                filename=file_path,
                output_format="wav",
            )

            thumbnail_result = await self.thumbnail_generator.generate_thumbnail(
                video_data=video_data,
                filename=file_path,
                size="medium",
                timestamp=5.0,
            )
            success = True
            duration = time.monotonic() - start_time
            logger.info(
                "video_processing.job.completed",
                media_id=str(media_id),
                duration=duration,
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "audio_extraction_result": audio_result,
                "thumbnail_generation_result": thumbnail_result,
                "message": "Video processed successfully",
            }
        except Exception as exc:
            logger.error(
                "video_processing.job.failed",
                media_id=str(media_id),
                error=str(exc),
                exc_info=True,
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            if self._metrics is not None:
                effective_file_size = (
                    file_size_bytes
                    if file_size_bytes is not None
                    else len(video_data) if "video_data" in locals() else 0
                )
                try:
                    await self._metrics.record_operation(
                        operation="process_video_job",
                        duration=duration,
                        success=success,
                        file_size_bytes=effective_file_size,
                    )
                except Exception as metrics_exc:  # pragma: no cover - best effort
                    logger.warning(
                        "video_processing.metrics_failed",
                        error=str(metrics_exc),
                    )

    def process_video_job_sync(
        self,
        *,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        file_size_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute video processing workflow synchronously for Celery tasks."""
        start_time = time.monotonic()
        success = False
        error_occurred = False
        video_data = b""
        provider = storage_provider or self._default_storage_provider
        logger.info(
            "video_processing.job.started_sync",
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=provider,
        )
        try:
            storage_service = self._storage_factory.get_download_service(provider)
            # Use sync download if available, otherwise use async in separate thread
            if hasattr(storage_service, 'download_file_sync'):
                video_data = storage_service.download_file_sync(file_path)
            else:
                import concurrent.futures
                def run_async():
                    import asyncio
                    return asyncio.run(storage_service.download_file(file_path))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    video_data = future.result()

            # Use sync methods if available
            if hasattr(self.audio_extractor, 'extract_audio_sync'):
                audio_result = self.audio_extractor.extract_audio_sync(
                    video_data=video_data,
                    filename=file_path,
                    output_format="wav",
                )
            else:
                import concurrent.futures
                def run_async():
                    import asyncio
                    return asyncio.run(
                        self.audio_extractor.extract_audio(
                            video_data=video_data,
                            filename=file_path,
                            output_format="wav",
                        )
                    )
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    audio_result = future.result()

            if hasattr(self.thumbnail_generator, 'generate_thumbnail_sync'):
                thumbnail_result = self.thumbnail_generator.generate_thumbnail_sync(
                    video_data=video_data,
                    filename=file_path,
                    size="medium",
                    timestamp=5.0,
                )
            else:
                import concurrent.futures
                def run_async():
                    import asyncio
                    return asyncio.run(
                        self.thumbnail_generator.generate_thumbnail(
                            video_data=video_data,
                            filename=file_path,
                            size="medium",
                            timestamp=5.0,
                        )
                    )
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    thumbnail_result = future.result()

            success = True
            duration = time.monotonic() - start_time
            logger.info(
                "video_processing.job.completed_sync",
                media_id=str(media_id),
                duration=duration,
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "audio_extraction_result": audio_result,
                "thumbnail_generation_result": thumbnail_result,
                "message": "Video processed successfully",
            }
        except Exception as exc:
            error_occurred = True
            logger.error(
                "video_processing.job.failed_sync",
                media_id=str(media_id),
                error=str(exc),
                exc_info=True,
            )
            raise
        finally:
            duration = time.monotonic() - start_time
            if self._metrics is not None:
                effective_file_size = (
                    file_size_bytes
                    if file_size_bytes is not None
                    else len(video_data) if 'video_data' in locals() and video_data else 0
                )
                # Use sync metrics if available
                if hasattr(self._metrics, 'record_operation_sync'):
                    try:
                        self._metrics.record_operation_sync(
                            operation="process_video_job",
                            duration=duration,
                            success=success,
                            file_size_bytes=effective_file_size,
                        )
                    except Exception as metrics_exc:  # pragma: no cover - best effort
                        logger.warning(
                            "video_processing.metrics_failed_sync",
                            error=str(metrics_exc),
                        )
                else:
                    # Use async metrics in separate thread if sync not available
                    import concurrent.futures
                    def run_async():
                        import asyncio
                        return asyncio.run(
                            self._metrics.record_operation(
                                operation="process_video_job",
                                duration=duration,
                                success=success,
                                file_size_bytes=effective_file_size,
                            )
                        )
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        try:
                            future = executor.submit(run_async)
                            future.result(timeout=5)  # Set a timeout to prevent hanging
                        except Exception as metrics_exc:
                            logger.warning(
                                "video_processing.metrics_failed_sync_thread",
                                error=str(metrics_exc),
                            )
