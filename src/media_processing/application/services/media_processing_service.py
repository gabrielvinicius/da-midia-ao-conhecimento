"""Application service that orchestrates media processing workflows."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.providers.domain.interfaces import IProviderRegistry, ProviderType
from src.media_processing.application.commands.dto import (
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
        transcription_metrics: Any | None = None,
        video_metrics: Any | None = None,
        provider_registry: IProviderRegistry | None = None,
    ) -> None:
        self._transcription_service = transcription_service
        self._video_service = video_service
        self._logger = structlog.get_logger(__name__).bind(component="media_processing.service")
        self._transcription_metrics = transcription_metrics
        self._video_metrics = video_metrics
        self._provider_registry = provider_registry

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
            ProviderType.TRANSCRIPTION,
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
    # Queries
    # ------------------------------------------------------------------ #
    async def get_transcription_by_media(self, media_id: UUID): # Needs a DTO
        """Return the latest transcription entity for the provided media ID."""
        return await self._transcription_service.get_transcription_by_media_id(media_id)

    async def get_transcription_details(self, transcription_id: UUID): # Needs a DTO
        """Return a transcription by its identifier."""
        return await self._transcription_service.get_transcription_by_id(transcription_id)

    # ------------------------------------------------------------------ #
    # Private Helpers
    # ------------------------------------------------------------------ #
    def _validate_provider(self, name: str | None, provider_type: ProviderType) -> str | None:
        if not name or self._provider_registry is None:
            return name
        active = {
            getattr(p, "name", None) or getattr(p, "get_name", lambda: None)()
            for p in self._provider_registry.get_active_providers(provider_type)
        }
        if name not in active:
            raise ValueError(f"Provider '{name}' not registered/active for {provider_type.value}")
        return name