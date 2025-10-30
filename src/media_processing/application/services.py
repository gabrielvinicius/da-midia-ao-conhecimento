"""Application service that orchestrates media processing workflows."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

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
from src.shared.events.domain_events import MediaUploaded, TextContentReady


class MediaProcessingService:
    """Facade that coordinates transcription and video processing pipelines."""

    def __init__(
        self,
        *,
        transcription_service: TranscriptionService,
        transcription_queries: TranscriptionQueries,
        video_service: VideoProcessingService,
    ) -> None:
        self._transcription_service = transcription_service
        self._transcription_queries = transcription_queries
        self._video_service = video_service
        self._logger = structlog.get_logger(__name__).bind(component="media_processing.service")

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
    ) -> Dict[str, Any]:
        """Schedule transcription generation using the consolidated service."""

        return await self._transcription_service.request_transcription_generation(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language,
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
    ) -> Dict[str, Any]:
        """Schedule asynchronous video processing for the uploaded media."""

        return await self._video_service.request_video_processing(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
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

        try:
            await self.request_transcription(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "media_uploaded.transcription_failed",
                media_id=str(media_id),
                error=str(exc),
            )

        try:
            await self.request_video_processing(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(
                "media_uploaded.video_failed",
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
