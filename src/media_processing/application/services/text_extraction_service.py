from __future__ import annotations

import mimetypes
import time
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.ports import (
    MetricsPort,
    OCRProviderPort,
    StoragePort,
    TextExtractionTaskSchedulerPort,
    TextExtractorPort,
    TranscriptionRepositoryPort,
)
from src.media_processing.application.services.processing_job import announce_started, staged_file
from src.media_processing.domain import InvalidTranscriptionTransitionError, Transcription, TranscriptionStatus
from src.media_processing.domain.errors import NoTextFoundError, UnsupportedFileTypeError
from src.shared.application.ports import ProcessingStatsPort
from src.shared.domain.errors import is_permanent_failure
from src.shared.domain.events import (
    MediaProcessingCompleted,
    MediaProcessingFailed,
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
        stats_recorder: ProcessingStatsPort | None = None,
    ):
        self._repo = repository
        self._task_scheduler = task_scheduler
        self._storage = storage_service
        self._text_extractor = text_extractor
        self._ocr_provider = ocr_provider
        self._event_bus = event_bus
        self._metrics = metrics
        self._logger = logger or structlog.get_logger(__name__)
        self._stats = stats_recorder

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
        transcription = await self._repo.get_by_media_id(media_id)
        if transcription is None:
            # O registro é criado ao agendar; sem ele, a mídia foi excluída
            # durante a espera na fila e não há onde guardar o texto.
            logger.warning("text_extraction.record_missing", media_id=str(media_id))
            return
        if transcription.is_finished:
            logger.warning("text_extraction.already_finished", media_id=str(media_id))
            await self._reannounce(media_id, transcription, correlation_id)
            return
        await announce_started(self._event_bus, media_id, "text_extraction", correlation_id)
        transcription.mark_as_processing()
        await self._repo.save(transcription)

        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        suffix = Path(file_path).suffix
        context = self._context(transcription, user_id, filename)
        started = time.perf_counter()
        provider_used, size = "text_extraction", 0
        try:
            async with staged_file(self._storage, file_path) as local:
                size = local.size_bytes
                extracted_text, provider_used = await self._extract(local.path, mime_type, suffix)
            if not extracted_text.strip():
                raise NoTextFoundError()
        except Exception as exc:
            await self._record_duration(time.perf_counter() - started, size, provider_used, "failed")
            # Arquivo ausente, tipo não suportado ou sem texto não mudam com
            # outra tentativa: a falha já é a definitiva.
            final = final_attempt or is_permanent_failure(exc)
            await self._record_failure(media_id, transcription, exc, final, context, correlation_id)
            raise
        await self._record_duration(time.perf_counter() - started, size, provider_used, "success")
        try:
            transcription.mark_as_extracted(extracted_text, provider_used)
        except InvalidTranscriptionTransitionError as exc:  # prazo vencido no meio da extração
            logger.warning("text_extraction.stale_result_ignored", media_id=str(media_id), reason=str(exc))
            return
        await self._repo.save(transcription)
        await self._announce_extracted(media_id, transcription, extracted_text, provider_used, context, correlation_id)

    @staticmethod
    def _context(transcription: Transcription, user_id: str | None, filename: str | None) -> Dict[str, Any]:
        owner = user_id or transcription.user_id
        return {"user_id": str(owner) if owner else None, "filename": filename or transcription.filename}

    async def _reannounce(self, media_id: UUID, transcription: Transcription, correlation_id: str | None) -> None:
        """Como na transcrição (TranscriptionRunner._reannounce): a tarefa voltou
        depois de terminar, e só o anúncio do resultado gravado é repetido."""
        context = self._context(transcription, None, None)
        correlation_id = correlation_id or transcription.correlation_id
        if transcription.status == TranscriptionStatus.COMPLETED:
            await self._announce_extracted(
                media_id, transcription, transcription.text, transcription.provider, context, correlation_id
            )
        elif self._event_bus:
            await self._event_bus.publish(
                MediaProcessingFailed(
                    media_id=str(media_id),
                    stage="text_extraction",
                    error_message=transcription.error_message or "A extração do texto falhou.",
                    user_id=context["user_id"],
                    correlation_id=correlation_id,
                )
            )

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
        raise UnsupportedFileTypeError(suffix)

    async def _record_duration(self, seconds: float, size: int, provider: str, status: str) -> None:
        """Tempo da extração, como o da transcrição: base das medições e estimativas."""
        if not self._stats:
            return
        try:
            await self._stats.log_stat("text_extraction", seconds, size, None, provider, status)
        except Exception as exc:  # estatística nunca derruba a extração
            logger.warning("text_extraction.stats_record_failed", error=str(exc))

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
        try:
            if final_attempt:
                transcription.mark_as_failed(str(exc))
            else:
                transcription.record_processing_error(str(exc))
        except InvalidTranscriptionTransitionError as stale:  # já dada como falha pelo prazo
            logger.warning("text_extraction.stale_failure_ignored", media_id=str(media_id), reason=str(stale))
            return
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
