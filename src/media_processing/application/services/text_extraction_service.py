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
    TextContentReady,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.domain.value_objects.file_path import FilePath

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
                    metadata={
                        "storage_provider": storage_provider,
                        "file_path": file_path,
                        "user_id": user_id,
                        "filename": filename,
                    },
                )
            )

        transcription = await self._repo.get_by_media_id(media_id)
        if transcription:
            transcription.mark_as_processing()
            await self._repo.save(transcription)

        # Retrieve content
        content = await self._storage.retrieve(FilePath(file_path))
        if not content:
            raise ResourceNotFoundError("File", file_path)

        suffix = Path(file_path).suffix
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        extracted_text = ""
        provider_used = "unknown"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if self._is_native_text(mime_type, suffix):
                provider_used = "text_extractor"
                extracted_text = await self._text_extractor.extract(tmp_path, mime_type)
            elif self._is_image(mime_type, suffix):
                provider_used = "ocr"
                extracted_text = await self._ocr_provider.extract(tmp_path)
            elif mime_type == "application/pdf" or suffix == ".pdf":
                text = await self._text_extractor.extract(tmp_path, mime_type)
                if len(text.strip()) < 50:
                    provider_used = "ocr_pdf"
                    extracted_text = await self._ocr_provider.extract(tmp_path)
                else:
                    provider_used = "pdf_native"
                    extracted_text = text
            else:
                provider_used = "fallback"
                extracted_text = ""

            if transcription:
                transcription.text = extracted_text
                transcription.status = TranscriptionStatus.COMPLETED
                transcription.provider = provider_used
                await self._repo.save(transcription)

                if self._event_bus:
                    await self._event_bus.publish(
                        MediaProcessingCompleted(
                            media_id=str(media_id),
                            stage="text_extraction",
                            result_id=str(transcription.id),
                            correlation_id=correlation_id,
                            metadata={
                                "provider": provider_used,
                                "storage_provider": storage_provider,
                                "file_path": file_path,
                                "user_id": user_id or getattr(transcription, "user_id", None),
                                "filename": filename or getattr(transcription, "filename", None),
                            },
                        )
                    )
                    await self._event_bus.publish(
                        TextContentReady(
                            media_id=str(media_id),
                            transcription_id=str(transcription.id),
                            text=extracted_text,
                            user_id=user_id or getattr(transcription, "user_id", None),
                            filename=filename
                            or getattr(transcription, "filename", None),
                            metadata={
                                "provider": provider_used,
                            },
                            correlation_id=correlation_id,
                        )
                    )

        except Exception as exc:
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
                        correlation_id=correlation_id,
                        metadata={
                            "storage_provider": storage_provider,
                            "file_path": file_path,
                            "user_id": user_id or getattr(transcription, "user_id", None),
                            "filename": filename or getattr(transcription, "filename", None),
                        },
                    )
                )
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

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
