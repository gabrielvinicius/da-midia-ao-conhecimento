"""Event handlers for the media_processing module."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.dtos import (
    RequestTextExtractionCommand,
    RequestTranscriptionCommand,
)
from src.shared.domain.events import MediaUploaded
from src.shared.domain.value_objects.identifiers import parse_id, parse_media_id

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

    async def handle_media_uploaded(self, event: MediaUploaded) -> None:
        """Trigger downstream processing whenever a media upload completes."""
        try:
            media_id = parse_media_id(event.media_id)
            media_type = self._resolve_media_type(event.media_type)

            # Documentos e imagens seguem para extração de texto (com OCR);
            # áudio e vídeo, para a transcrição, que lê o arquivo original.
            if media_type == TEXT_MEDIA_TYPE:
                await self._delegate_text_extraction(event, media_id)
            else:
                await self._delegate_transcription(event, media_id)

        except Exception as exc:  # pragma: no cover - defensive catch
            self._logger.error(
                "media_uploaded.handler_failed",
                media_id=getattr(event, "media_id", None),
                error=str(exc),
                correlation_id=getattr(event, "correlation_id", None),
            )
            return

    async def _delegate_text_extraction(self, event: MediaUploaded, media_id: UUID) -> None:
        try:
            command = RequestTextExtractionCommand(
                media_id=media_id,
                file_path=event.file_path,
                storage_provider=event.storage_provider or "local",
                user_id=parse_id(event.user_id),
                filename=event.filename,
                correlation_id=event.correlation_id,
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

    async def _delegate_transcription(self, event: MediaUploaded, media_id: UUID) -> None:
        try:
            command = RequestTranscriptionCommand(
                media_id=media_id,
                file_path=event.file_path,
                storage_provider=event.storage_provider or "local",
                transcription_provider=event.transcription_provider or "default",
                language=event.language or "auto",
                file_size_bytes=event.file_size_bytes or 0,
                user_id=parse_id(event.user_id),
                filename=event.filename,
                correlation_id=event.correlation_id,
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

