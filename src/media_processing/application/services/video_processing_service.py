# src/video_processing/application/video_processing_service.py
"""Consolidated Video Processing Service."""
import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.ports import (
    MetricsPort,
    StorageServiceFactoryPort,
    VideoAudioExtractorPort,
    VideoThumbnailGeneratorPort,
)
from src.shared.domain.events import MediaProcessingCompleted
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus

logger = structlog.get_logger(__name__)


class VideoProcessingService:
    """Consolidated service for all video processing operations."""

    def __init__(
        self,
        video_audio_extractor: VideoAudioExtractorPort,
        video_thumbnail_generator: VideoThumbnailGeneratorPort,
        video_processing_task_scheduler: Any,
        storage_factory: StorageServiceFactoryPort,
        default_storage_provider: str = "local",
        video_processing_metrics: Optional[MetricsPort] = None,
        event_bus: Optional[SupportsEventBus] = None,
    ):
        self.audio_extractor = video_audio_extractor
        self.thumbnail_generator = video_thumbnail_generator
        self.task_scheduler = video_processing_task_scheduler
        self._storage_factory = storage_factory
        self._default_storage_provider = default_storage_provider
        self._metrics = video_processing_metrics
        self._event_bus = event_bus

    async def request_video_processing(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        user_id: Optional[UUID] = None,
        filename: Optional[str] = None,
        triggered_by: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule video processing for a media item."""
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
                user_id=str(user_id) if user_id else None,
                filename=filename,
                triggered_by=triggered_by,
                actor_id=actor_id,
                correlation_id=correlation_id or str(media_id),
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
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filename: Optional[str] = None,
        triggered_by: Optional[str] = None,
        actor_id: Optional[str] = None,
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

            if self._event_bus and audio_result.get("success"):
                await self._event_bus.publish(
                    MediaProcessingCompleted(
                        media_id=str(media_id),
                        stage="audio_extraction",
                        result_id=audio_result.get("audio_file_path", ""),
                        metadata={
                            "storage_provider": provider,
                            "filename": filename,
                            "user_id": user_id,
                            "triggered_by": triggered_by,
                            "actor_id": actor_id,
                        },
                        correlation_id=correlation_id or str(media_id),
                    )
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
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filename: Optional[str] = None,
        triggered_by: Optional[str] = None,
        actor_id: Optional[str] = None,
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
                    else len(video_data)
                    if "video_data" in locals() and video_data
                    else 0
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
