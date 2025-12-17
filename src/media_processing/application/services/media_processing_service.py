"""Application service that orchestrates media processing workflows."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Set
from uuid import UUID

import structlog

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.config.settings import processing_settings

from ..dtos import (
    RequestTextExtractionCommand,
    RequestTranscriptionCommand,
    RequestVideoProcessingCommand,
)


class MediaProcessingService:
    """Facade that coordinates transcription and video processing pipelines."""

    def __init__(
        self,
        *,
        transcription_service: TranscriptionService,
        video_service: VideoProcessingService,
        text_extraction_service: TextExtractionService,
        transcription_metrics: Any | None = None,
        video_metrics: Any | None = None,
    ) -> None:
        self._transcription_service = transcription_service
        self._video_service = video_service
        self._text_extraction_service = text_extraction_service
        self._logger = structlog.get_logger(__name__).bind(
            component="media_processing.service"
        )
        self._transcription_metrics = transcription_metrics
        self._video_metrics = video_metrics
        # Soft allowlists per provider kind; warn if outside.
        self._allowed_transcription = set(
            processing_settings.transcription_providers_allowed or []
        )

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #
    async def request_transcription(
        self,
        command: RequestTranscriptionCommand,
        metrics_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule transcription generation using the consolidated service."""
        transcription_provider = self._validate_provider(
            command.transcription_provider,
            self._allowed_transcription,
            "transcription_provider",
        )

        start_time = time.monotonic()
        success = False
        try:
            result = await self._transcription_service.request_transcription_generation(
                media_id=command.media_id,
                file_path=command.file_path,
                storage_provider=command.storage_provider,
                transcription_provider=transcription_provider,
                language=command.language,
                user_id=str(command.user_id) if command.user_id else None,
                filename=command.filename,
                triggered_by=command.triggered_by,
                actor_id=command.actor_id,
                correlation_id=command.correlation_id,
                summarization_provider=command.summarization_provider,
                sentiment_provider=command.sentiment_provider,
                topic_modeling_provider=command.topic_modeling_provider,
                file_size_bytes=command.file_size_bytes,
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
                        input_audio_length_seconds=payload.get(
                            "input_audio_length_seconds", 0.0
                        ),
                        output_text_length_chars=payload.get(
                            "output_text_length_chars", 0
                        ),
                    )
                except Exception as exc:  # pragma: no cover - metrics should not break
                    self._logger.warning(
                        "transcription_metrics.record_failed",
                        error=str(exc),
                    )

    async def request_video_processing(
        self,
        command: RequestVideoProcessingCommand,
        metrics_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Schedule asynchronous video processing for the uploaded media."""
        start_time = time.monotonic()
        success = False
        try:
            result = await self._video_service.request_video_processing(
                media_id=command.media_id,
                file_path=command.file_path,
                storage_provider=command.storage_provider,
                user_id=command.user_id,
                filename=command.filename,
                triggered_by=command.triggered_by,
                actor_id=command.actor_id,
                correlation_id=command.correlation_id,
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

    async def request_text_extraction(
        self,
        command: RequestTextExtractionCommand,
    ) -> Dict[str, Any]:
        """Schedule text extraction for the uploaded media."""
        # Simple delegation for now
        return await self._text_extraction_service.request_text_extraction(command)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    async def get_transcription_by_media(self, media_id: UUID):
        # Needs a DTO
        """Return the latest transcription entity for the provided media ID."""
        return await self._transcription_service.get_transcription_by_media_id(
            media_id
        )

    async def get_transcription_details(self, transcription_id: UUID):
        # Needs a DTO
        """Return a transcription by its identifier."""
        return await self._transcription_service.get_transcription_by_id(
            transcription_id
        )

    # ------------------------------------------------------------------ #
    # Private Helpers
    # ------------------------------------------------------------------ #
    def _validate_provider(
        self,
        name: str | None,
        allowed: Set[str],
        field: str,
    ) -> str | None:
        if name is None:
            return None
        if allowed and name not in allowed:
            self._logger.warning(
                "media_processing.provider.unrecognized",
                field=field,
                provider=name,
                allowed=list(sorted(allowed)),
            )
        return name
