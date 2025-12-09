from __future__ import annotations
import asyncio
import tempfile
import os
import mimetypes
from uuid import UUID
from typing import Any, Dict, Optional
from pathlib import Path

import structlog

from src.media_processing.application.commands.dto import RequestTextExtractionCommand
from src.media_processing.infrastructure.text.task_scheduler import CeleryTextTaskScheduler
from src.media_processing.infrastructure.transcription.transcription_repository import TranscriptionRepository
from src.media_processing.domain.model import Transcription, TranscriptionStatus
from src.shared.infrastructure.event_bus import SupportsEventBus
from src.shared.domain.events import MediaProcessingStarted, MediaProcessingCompleted, MediaProcessingFailed, TextContentReady
from src.storage.domain.value_objects.file_path import FilePath
from src.shared.domain.errors import ResourceNotFoundError

logger = structlog.get_logger(__name__)

class TextExtractionService:
    def __init__(
        self,
        repository: TranscriptionRepository,
        task_scheduler: CeleryTextTaskScheduler,
        storage_service: Any,
        event_bus: SupportsEventBus | None = None,
        text_extractor: Any = None,
        ocr_provider: Any = None,
    ):
        self._repo = repository
        self._task_scheduler = task_scheduler
        self._storage = storage_service
        self._event_bus = event_bus
        self._text_extractor = text_extractor
        self._ocr_provider = ocr_provider

    async def request_text_extraction(self, command: RequestTextExtractionCommand) -> Dict[str, Any]:
        """Schedules text extraction task."""
        transcription = Transcription(
            media_id=command.media_id,
            status=TranscriptionStatus.PENDING,
            provider="text_extraction"
        )
        await self._repo.save(transcription)
        
        task_info = await self._task_scheduler.schedule_text_extraction(
            media_id=command.media_id,
            file_path=command.file_path,
            storage_provider=command.storage_provider
        )
        
        return {"task_id": task_info.get("task_id"), "extraction_id": str(transcription.id)}

    async def execute_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str
    ) -> None:
        """Executes the actual extraction logic."""
        if self._event_bus:
            await self._event_bus.publish(MediaProcessingStarted(media_id=str(media_id)))

        transcription = await self._repo.get_by_media_id(media_id)
        
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
                    await self._event_bus.publish(MediaProcessingCompleted(media_id=str(media_id)))
                    await self._event_bus.publish(TextContentReady(
                        media_id=str(media_id),
                        transcription_id=str(transcription.id),
                        text_content=extracted_text,
                        metadata={"provider": provider_used}
                    ))

        except Exception as exc:
            if transcription:
                transcription.status = TranscriptionStatus.FAILED
                transcription.error_message = str(exc)
                await self._repo.save(transcription)
            if self._event_bus:
                await self._event_bus.publish(MediaProcessingFailed(media_id=str(media_id), error_message=str(exc)))
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _is_native_text(self, mime: str, ext: str) -> bool:
        return mime.startswith("text/") or ext in [".txt", ".csv", ".md", ".json", ".xml", ".docx"]

    def _is_image(self, mime: str, ext: str) -> bool:
        return mime.startswith("image/") or ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
