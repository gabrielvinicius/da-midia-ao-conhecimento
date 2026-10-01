"""Event handlers for the media_processing module."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

import structlog

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.shared.domain.events import MediaUploaded

TEXT_MEDIA_TYPE = "text"

logger = structlog.get_logger(__name__).bind(
    component="media_processing.event_handlers"
)


class MediaProcessingEventHandlers:
    """Handles domain events related to media processing."""

    def __init__(
        self,
        transcription_service: TranscriptionService,
        text_extraction_service: TextExtractionService,
    ) -> None:
        self._transcription_service = transcription_service
        self._text_extraction_service = text_extraction_service
        self._logger = structlog.get_logger(__name__).bind(
            component="media_processing.event_handlers"
        )

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
            media_type_value = event.media_type or context.get("media_type")
            media_type = self._resolve_media_type(media_type_value)

            # Documentos e imagens seguem para extração de texto (com OCR);
            # áudio e vídeo, para a transcrição, que lê o arquivo original.
            if media_type == TEXT_MEDIA_TYPE:
                await self._delegate_text_extraction(event, context, media_id)
            else:
                await self._delegate_transcription(event, context, media_id)

        except Exception as exc:  # pragma: no cover - defensive catch
            self._logger.error(
                "media_uploaded.handler_failed",
                media_id=getattr(event, "media_id", None),
                error=str(exc),
                correlation_id=getattr(event, "correlation_id", None),
            )
            return

    async def _delegate_text_extraction(self, event, context, media_id):
        storage_provider = (
            event.storage_provider or context.get("storage_provider") or "local"
        )
        file_path = getattr(event, "file_path", None) or context.get("file_path")
        user_uuid = None
        try:
            user_uuid = UUID(event.user_id) if event.user_id else None
        except Exception:
            user_uuid = None

        try:
            from src.media_processing.application.dtos import (
                RequestTextExtractionCommand,
            )
            command = RequestTextExtractionCommand(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
                user_id=user_uuid,
                filename=getattr(event, "filename", None),
                triggered_by=getattr(event, "triggered_by", None),
                actor_id=getattr(event, "actor_id", None) or context.get("actor_id"),
                correlation_id=getattr(event, "correlation_id", None),
            )
            await self._text_extraction_service.request_text_extraction(command)
            self._logger.debug(
                "media_uploaded.text_extraction_delegated",
                media_id=str(media_id),
            )
        except Exception as exc:
            self._logger.error(
                "media_uploaded.text_extraction_delegation_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    async def _delegate_transcription(self, event, context, media_id):
        storage_provider = (
            event.storage_provider or context.get("storage_provider") or "local"
        )
        # Validate providers
        transcription_provider = (
            event.transcription_provider
            or context.get("transcription_provider")
            or context.get("provider")
            or "default"
        )
        summarization_provider = (
            event.summarization_provider or context.get("summarization_provider")
        )
        sentiment_provider = (
            event.sentiment_provider or context.get("sentiment_provider")
        )
        topic_provider = (
            event.topic_modeling_provider or context.get("topic_modeling_provider")
        )

        file_path = getattr(event, "file_path", None) or context.get("file_path")
        user_uuid = None
        try:
            user_uuid = UUID(event.user_id) if event.user_id else None
        except Exception:
            user_uuid = None

        try:
            from src.media_processing.application.dtos import (
                RequestTranscriptionCommand,
            )
            command = RequestTranscriptionCommand(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=event.language or context.get("language") or "auto",
                file_size_bytes=(
                    event.file_size_bytes or context.get("file_size_bytes") or 0
                ),
                summarization_provider=summarization_provider,
                sentiment_provider=sentiment_provider,
                topic_modeling_provider=topic_provider,
                user_id=user_uuid,
                filename=getattr(event, "filename", None),
                triggered_by=getattr(event, "triggered_by", None),
                actor_id=getattr(event, "actor_id", None) or context.get("actor_id"),
                correlation_id=getattr(event, "correlation_id", None),
            )
            await self._transcription_service.request_transcription_generation(command)
            self._logger.debug(
                "media_uploaded.transcription_delegated",
                media_id=str(media_id),
            )
        except Exception as exc:
            self._logger.error(
                "media_uploaded.transcription_delegation_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    @staticmethod
    def _resolve_media_type(media_type_value) -> Optional[str]:
        """Tipo da mídia como texto ("text", "audio", "video").

        O evento carrega o valor do enum de media_management; este módulo
        compara pelo valor para não depender do domínio de outro módulo.
        """
        if media_type_value is None:
            return None
        value = getattr(media_type_value, "value", media_type_value)
        return str(value).strip().lower() or None

    def _validate_provider(self, name: str | None) -> str | None:
        return name
