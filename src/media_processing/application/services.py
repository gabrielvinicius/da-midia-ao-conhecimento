"""Application service that orchestrates media processing workflows."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from pydantic import ValidationError

from src.media_processing.application.schemas import (
    TranscriptionTaskPayload,
    VideoTaskPayload,
)
from src.media_processing.tasks import process_transcription_task, process_video_task
from src.media_processing.transcription.application.queries.transcription_queries import (
    TranscriptionQueries,
)
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.media_processing.video_processing.application.video_processing_service import (
    VideoProcessingService,
)
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

        storage_provider = event.storage_provider or context.get("storage_provider") or "local"
        transcription_provider = (
            event.transcription_provider
            or context.get("transcription_provider")
            or context.get("provider")
            or "fastwhisper"
        )
        summarization_provider = event.summarization_provider or context.get("summarization_provider")
        sentiment_provider = event.sentiment_provider or context.get("sentiment_provider")
        topic_provider = event.topic_modeling_provider or context.get("topic_modeling_provider")
        language = event.language or context.get("language") or "en"
        file_size_bytes = event.file_size_bytes or context.get("file_size_bytes") or 0
        media_type_value = event.media_type or context.get("media_type")
        media_type = None
        media_enum = None
        try:
            from src.media_management.domain.enums import MediaType as _MediaType

            media_enum = _MediaType
            if isinstance(media_type_value, _MediaType):
                media_type = media_type_value
            elif media_type_value is not None:
                candidate = str(media_type_value).upper()
                media_type = _MediaType(candidate)
        except Exception:
            media_type = None

        if media_enum and media_type == media_enum.TEXT:
            self._logger.debug(
                "media_uploaded.transcription_task_skipped",
                media_id=str(media_id),
                reason="text_document",
            )
        else:
            try:
                transcription_payload = TranscriptionTaskPayload(
                    media_id=media_id,
                    file_path=file_path,
                    storage_provider=storage_provider,
                    transcription_provider=transcription_provider,
                    language=language,
                    summarization_provider=summarization_provider,
                    sentiment_provider=sentiment_provider,
                    topic_modeling_provider=topic_provider,
                    file_size_bytes=file_size_bytes,
                )
                process_transcription_task.delay(
                    **transcription_payload.model_dump(mode="json")
                )
                self._logger.debug(
                    "media_uploaded.transcription_task_enqueued",
                    media_id=str(media_id),
                    storage_provider=storage_provider,
                    transcription_provider=transcription_provider,
                    language=language,
                )
            except ValidationError as exc:
                self._logger.error(
                    "media_uploaded.transcription_payload_invalid",
                    media_id=str(media_id),
                    errors=exc.errors(),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                self._logger.error(
                    "media_uploaded.transcription_enqueue_failed",
                    media_id=str(media_id),
                    error=str(exc),
                )

        if media_enum and media_type == media_enum.VIDEO:
            try:
                video_payload = VideoTaskPayload(
                    media_id=media_id,
                    file_path=file_path,
                    storage_provider=storage_provider,
                    file_size_bytes=file_size_bytes,
                )
                process_video_task.delay(**video_payload.model_dump(mode="json"))
                self._logger.debug(
                    "media_uploaded.video_task_enqueued",
                    media_id=str(media_id),
                    storage_provider=storage_provider,
                    file_size_bytes=file_size_bytes,
                )
            except ValidationError as exc:
                self._logger.error(
                    "media_uploaded.video_payload_invalid",
                    media_id=str(media_id),
                    errors=exc.errors(),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                self._logger.error(
                    "media_uploaded.video_enqueue_failed",
                    media_id=str(media_id),
                    error=str(exc),
                )
        else:
            self._logger.debug(
                "media_uploaded.video_task_skipped",
                media_id=str(media_id),
                reason="non_video_media",
                media_type=str(media_type) if media_type else str(media_type_value),
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
