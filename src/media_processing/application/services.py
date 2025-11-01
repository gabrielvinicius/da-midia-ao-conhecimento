"""Application service that orchestrates media processing workflows."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID
import time

import structlog

from src.media_processing.transcription.application.queries.transcription_queries import (
    TranscriptionQueries,
)
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.tasks import process_transcription_task, process_video_task
from src.shared.events.domain_events import MediaUploaded, TextContentReady


class MediaProcessingService:
    """Facade that coordinates transcription and video processing pipelines."""

    def __init__(
        self,
        *,
        transcription_service: TranscriptionService,
        transcription_queries: TranscriptionQueries,
        video_service: VideoProcessingService,
        transcription_metrics: Any | None = None,
        video_metrics: Any | None = None,
    ) -> None:
        self._transcription_service = transcription_service
        self._transcription_queries = transcription_queries
        self._video_service = video_service
        self._logger = structlog.get_logger(__name__).bind(component="media_processing.service")
        self._transcription_metrics = transcription_metrics
        self._video_metrics = video_metrics

    # ------------------------------------------------------------------ #
    # Transcription helpers
    # ------------------------------------------------------------------ #
    async def request_transcription(
        self,
        *,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        metrics_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule transcription generation using the consolidated service."""

        start_time = time.monotonic()
        success = False
        try:
            result = await self._transcription_service.request_transcription_generation(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
            )
            success = True
            return result
        finally:
            if self._transcription_metrics is not None:
                payload = metrics_payload or {}
                try:
                    await self._transcription_metrics.record_operation(
                        operation="request_transcription",
                        provider=transcription_provider,
                        duration=payload.get("duration", time.monotonic() - start_time),
                        success=success,
                        input_audio_length_seconds=payload.get("input_audio_length_seconds", 0.0),
                        output_text_length_chars=payload.get("output_text_length_chars", 0),
                    )
                except Exception as exc:  # pragma: no cover - metrics should not break flow
                    self._logger.warning(
                        "transcription_metrics.record_failed",
                        error=str(exc),
                    )

    async def get_transcription_by_media(self, media_id: UUID):
        """Return the latest transcription entity for the provided media ID."""

        return await self._transcription_service.get_transcription_by_media_id(media_id)

    async def get_transcription_details(self, transcription_id: UUID):
        """Return a transcription by its identifier."""

        return await self._transcription_queries.get_by_id(transcription_id)

    # ------------------------------------------------------------------ #
    # Video helpers
    # ------------------------------------------------------------------ #
    async def request_video_processing(
        self,
        *,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        metrics_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule asynchronous video processing for the uploaded media."""

        start_time = time.monotonic()
        success = False
        try:
            result = await self._video_service.request_video_processing(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
            )
            success = True
            return result
        finally:
            if self._video_metrics is not None:
                payload = metrics_payload or {}
                try:
                    await self._video_metrics.record_operation(
                        operation="request_video_processing",
                        duration=payload.get("duration", time.monotonic() - start_time),
                        success=success,
                        file_size_bytes=payload.get("file_size_bytes", 0),
                    )
                except Exception as exc:  # pragma: no cover
                    self._logger.warning(
                        "video_metrics.record_failed",
                        error=str(exc),
                    )

    # ------------------------------------------------------------------ #
    # Event Handlers
    # ------------------------------------------------------------------ #
    async def handle_media_uploaded(
        self,
        event: MediaUploaded,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Trigger downstream processing whenever a media upload completes."""

        context = context or {}

        try:
            media_id = UUID(event.media_id)
        except (ValueError, TypeError) as exc:
            self._logger.warning(
                "media_uploaded.invalid_media_id",
                media_id=event.media_id,
                error=str(exc),
            )
            return

        file_path = (
            context.get("file_path")
            or getattr(event, "file_path", None)
            or event.filename
        )
        if not file_path:
            self._logger.warning(
                "media_uploaded.missing_file_path",
                media_id=str(media_id),
            )
            return

        storage_provider = context.get("storage_provider") or event.storage_provider or "local"
        transcription_provider = context.get("transcription_provider") or context.get("provider") or "default"
        language = context.get("language", "en")
        file_size_bytes = context.get("file_size_bytes", 0)

        try:
            process_transcription_task.delay(
                media_id=str(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
            )
            self._logger.debug(
                "media_uploaded.transcription_task_enqueued",
                media_id=str(media_id),
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "media_uploaded.transcription_enqueue_failed",
                media_id=str(media_id),
                error=str(exc),
            )

        try:
            process_video_task.delay(
                media_id=str(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
            )
            self._logger.debug(
                "media_uploaded.video_task_enqueued",
                media_id=str(media_id),
                storage_provider=storage_provider,
                file_size_bytes=file_size_bytes,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "media_uploaded.video_enqueue_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    async def handle_text_content_ready(
        self,
        event: TextContentReady,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Placeholder hook for when derived textual content becomes available."""

        context = context or {}
        self._logger.info(
            "text_content_ready.received",
            media_id=event.media_id,
            transcription_id=event.transcription_id,
            summary_id=event.summary_id,
            context_keys=list(context.keys()),
        )
