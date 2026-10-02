from __future__ import annotations

import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.ports import (
    MetricsPort, # Add this
    OCRProviderPort,
    StoragePort,
    TextExtractionTaskSchedulerPort,
    TextExtractorPort,
    TranscriptionRepositoryPort,
)
from src.media_processing.domain import Transcription, TranscriptionStatus
from src.shared.domain.errors import ResourceNotFoundError
from src.shared.domain.events import (
    MediaProcessingCompleted,
    MediaProcessingFailed,
    MediaProcessingStarted,
    TranscriptionCompleted,
)
from src.shared.application.event_bus import SupportsEventBus

from ..dtos import RequestTextExtractionCommand

logger = structlog.get_logger(__name__)

class TextExtractionService:
    def __init__(
        self,
        repository: TranscriptionRepositoryPort,
        task_scheduler: Optional[TextExtractionTaskSchedulerPort],
        storage_service: StoragePort,
        text_extractor: TextExtractorPort,
        ocr_provider: OCRProviderPort,
        event_bus: SupportsEventBus | None = None,
        metrics: Optional[MetricsPort] = None,
        logger: Optional[Any] = None,
    ):
        self._repo = repository
        self._task_scheduler = task_scheduler
        self._storage = storage_service
        self._text_extractor = text_extractor
        self._ocr_provider = ocr_provider
        self._event_bus = event_bus
        self._metrics = metrics
        self._logger = logger or structlog.get_logger(__name__)

    async def request_text_extraction(
        self, command: RequestTextExtractionCommand
    ) -> Dict[str, Any]:
        """Schedules text extraction task."""
        transcription = Transcription(
            media_id=command.media_id,
            user_id=command.user_id,
            filename=command.filename,
            correlation_id=command.correlation_id,
            status=TranscriptionStatus.PENDING,
            provider="text_extraction",
        )
        await self._repo.save(transcription)

        task_info = await self._task_scheduler.schedule_text_extraction(
            media_id=command.media_id,
            file_path=command.file_path,
            storage_provider=command.storage_provider,
            user_id=str(command.user_id) if command.user_id else None,
            filename=command.filename,
            triggered_by=command.triggered_by,
            actor_id=command.actor_id,
            correlation_id=command.correlation_id,
        )

        return {
            "task_id": task_info.get("task_id"),
            "extraction_id": str(transcription.id),
        }

    async def execute_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        *,
        final_attempt: bool = False,
        correlation_id: str | None = None,
        user_id: str | None = None,
        filename: str | None = None,
    ) -> None:
        """Executes the actual extraction logic."""
        if self._event_bus:
            await self._event_bus.publish(
                MediaProcessingStarted(
                    media_id=str(media_id),
                    stage="text_extraction",
                    correlation_id=correlation_id,
                )
            )

        transcription = await self._repo.get_by_media_id(media_id)
        if transcription:
            transcription.mark_as_processing()
            await self._repo.save(transcription)

        # Retrieve content
        content = await self._storage.retrieve(file_path)
        if not content:
            raise ResourceNotFoundError("File", file_path)

        suffix = Path(file_path).suffix
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        owner = user_id or getattr(transcription, "user_id", None)
        context = {
            "user_id": str(owner) if owner else None,
            "filename": filename or getattr(transcription, "filename", None),
        }
        try:
            extracted_text, provider_used = await self._extract(tmp_path, mime_type, suffix)
            if transcription:
                transcription.mark_as_extracted(extracted_text, provider_used)
                await self._repo.save(transcription)
                await self._announce_extracted(
                    media_id, transcription, extracted_text, provider_used, context, correlation_id
                )
        except Exception as exc:  # registra a falha e devolve à fila para nova tentativa
            await self._record_failure(
                media_id, transcription, exc, final_attempt, context, correlation_id
            )
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _extract(self, path: str, mime_type: str, suffix: str) -> tuple[str, str]:
        """Texto do arquivo e o método usado: leitura direta, OCR ou PDF (com OCR
        quando o PDF não tem texto, como um documento escaneado)."""
        if self._is_native_text(mime_type, suffix):
            return await self._text_extractor.extract(path, mime_type), "text_extractor"
        if self._is_image(mime_type, suffix):
            return await self._ocr_provider.extract(path), "ocr"
        if mime_type == "application/pdf" or suffix == ".pdf":
            text = await self._text_extractor.extract(path, mime_type)
            if len(text.strip()) < 50:
                return await self._ocr_provider.extract(path), "ocr_pdf"
            return text, "pdf_native"
        return "", "fallback"

    async def _announce_extracted(
        self, media_id, transcription, text, provider_used, context, correlation_id
    ) -> None:
        if not self._event_bus:
            return
        await self._event_bus.publish(
            MediaProcessingCompleted(
                media_id=str(media_id),
                stage="text_extraction",
                result_id=str(transcription.id),
                correlation_id=correlation_id,
                provider=provider_used,
            )
        )
        # Como na transcrição de áudio: o módulo de mídias conclui a
        # mídia e anuncia o texto pronto para a análise.
        await self._event_bus.publish(
            TranscriptionCompleted(
                media_id=str(media_id),
                transcription_id=str(transcription.id),
                text=text,
                user_id=context["user_id"],
                provider=provider_used,
                filename=context["filename"],
                language=transcription.language,
                correlation_id=correlation_id,
            )
        )

    async def _record_failure(
        self, media_id, transcription, exc, final_attempt, context, correlation_id
    ) -> None:
        if transcription:
            if final_attempt:
                transcription.mark_as_failed(str(exc))
            else:
                transcription.record_processing_error(str(exc))
            await self._repo.save(transcription)
        if self._event_bus and final_attempt:
            await self._event_bus.publish(
                MediaProcessingFailed(
                    media_id=str(media_id),
                    stage="text_extraction",
                    error_message=str(exc),
                    user_id=context["user_id"],
                    correlation_id=correlation_id,
                )
            )

    def _is_native_text(self, mime: str, ext: str) -> bool:
        return mime.startswith("text/") or ext in [
            ".txt",
            ".csv",
            ".md",
            ".json",
            ".xml",
            ".docx",
        ]

    def _is_image(self, mime: str, ext: str) -> bool:
        return mime.startswith("image/") or ext in [
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".bmp",
        ]
