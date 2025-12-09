# src/media_processing/application/services/transcription_service.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional, List
from uuid import UUID

import structlog

from src.media_processing.domain.model import Transcription, TranscriptionStatus
from src.media_processing.infrastructure.transcription.transcription_repository import (
    TranscriptionRepository,
)
from src.media_processing.infrastructure.transcription.metrics import (
    PrometheusTranscriptionMetrics,
)
from src.media_processing.infrastructure.transcription.task_scheduler import (
    CeleryTranscriptionTaskScheduler,
)
from src.shared.infrastructure.event_bus import SupportsEventBus
import asyncio
import os
import tempfile
from pathlib import Path
from src.shared.domain.events import TranscriptionCompleted, TranscriptionFailed, MediaProcessingStarted
from src.storage.domain.value_objects.file_path import FilePath
from src.media_processing.infrastructure.transcription.logging import (
    StructuredTranscriptionLogger,
)
from src.shared.domain.errors import ResourceNotFoundError

# DTOs
from src.media_processing.application.commands.dto import (
    RequestTranscriptionCommand,
    SetSpeakerAliasesCommand,
    ReprocessTranscriptionCommand,
)
from src.media_processing.application.queries.dto import (
    GetTranscriptionByMediaIdQuery,
    GetTranscriptionByIdQuery,
)


logger = structlog.get_logger(__name__)


class TranscriptionService:
    """Handles all transcription-related operations, including requests and management."""

    def __init__(
        self,
        transcription_repo: TranscriptionRepository,
        task_scheduler: CeleryTranscriptionTaskScheduler,
        transcription_logger: StructuredTranscriptionLogger,
        transcription_metrics: PrometheusTranscriptionMetrics,
        storage_service: Any,
        speech_recognizer_factory: Callable[[str], Any],
        media_queries: Any,  # Duck typing for media_service.get_media
        event_bus: SupportsEventBus | None = None,
    ) -> None:
        self._repo = transcription_repo
        self._task_scheduler = task_scheduler
        self._logger = transcription_logger
        self._metrics = transcription_metrics
        self._storage = storage_service
        self._speech_recognizer_factory = speech_recognizer_factory
        self._media_queries = media_queries
        self._event_bus = event_bus

    async def execute_transcription(
        self,
        transcription_id: UUID,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes the transcription process: download, transcribe, and publish results."""
        if self._event_bus:
            await self._event_bus.publish(MediaProcessingStarted(media_id=str(media_id)))

        # Retrieve File
        content = await self._storage.retrieve(FilePath(file_path))
        if not content:
             raise ResourceNotFoundError("File", file_path)

        # Write to temp
        suffix = Path(file_path).suffix or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
            
        try:
            recognizer = self._speech_recognizer_factory(transcription_provider)
            # Support both sync and async recognizers
            if asyncio.iscoroutinefunction(recognizer.transcribe):
                result = await recognizer.transcribe(tmp_path, language=language)
            else:
                result = await asyncio.to_thread(recognizer.transcribe, tmp_path, language=language)
            
            # Inject downstream provider preferences into result metadata for the event
            result["summarization_provider"] = summarization_provider
            result["sentiment_provider"] = sentiment_provider
            result["topic_modeling_provider"] = topic_modeling_provider

            await self.process_transcription_result(
                transcription_id, media_id, result, transcription_provider, success=True
            )
            return result
        except Exception as exc:
            await self.process_transcription_result(
                transcription_id, media_id, {}, transcription_provider, success=False, error_message=str(exc)
            )
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def request_transcription_generation(self, command: RequestTranscriptionCommand) -> Dict[str, Any]:
        """Orchestrates the process of requesting a new transcription."""
        start_time = time.monotonic()
        success = False
        transcription_id: Optional[UUID] = None
        
        try:
            # 1. Create a PENDING transcription record
            transcription = Transcription(
                media_id=command.media_id,
                language=command.language,
                provider=command.transcription_provider,
                status=TranscriptionStatus.PENDING,
            )
            saved_transcription = await self._repo.save(transcription)
            transcription_id = saved_transcription.id

            # 2. Schedule the actual processing task
            task_info = await self._task_scheduler.schedule_transcription(
                transcription_id=transcription_id,
                media_id=command.media_id,
                file_path=command.file_path,
                storage_provider=command.storage_provider,
                transcription_provider=command.transcription_provider,
                language=command.language,
                file_size_bytes=command.file_size_bytes,
                summarization_provider=command.summarization_provider,
                sentiment_provider=command.sentiment_provider,
                topic_modeling_provider=command.topic_modeling_provider,
            )
            success = True
            self._logger.log_operation(
                operation="request_transcription_generation",
                media_id=str(command.media_id),
                transcription_id=str(transcription_id),
                status="SCHEDULED",
            )
            return {"task_id": task_info.get("task_id"), "transcription_id": str(transcription_id)}
        finally:
            self._metrics.set_context(str(command.media_id))
            await self._metrics.record_operation(
                operation="request_transcription",
                provider=command.transcription_provider,
                duration=time.monotonic() - start_time,
                success=success,
                status="SCHEDULED" if success else "FAILED",
            )

    async def set_speaker_aliases(self, command: SetSpeakerAliasesCommand) -> Transcription:
        """Sets or updates speaker aliases for a given transcription."""
        transcription = await self._repo.get_by_id(command.transcription_id)
        if not transcription:
            raise ResourceNotFoundError("Transcription", str(command.transcription_id))
        transcription.set_speaker_aliases(command.aliases)
        return await self._repo.save(transcription)

    async def get_transcription_by_media_id(self, query: GetTranscriptionByMediaIdQuery) -> Optional[Transcription]:
        """Retrieves transcription by media ID."""
        return await self._repo.get_by_media_id(query.media_id)

    async def get_transcription_by_id(self, query: GetTranscriptionByIdQuery) -> Optional[Transcription]:
        """Retrieves transcription by its ID."""
        return await self._repo.get_by_id(query.transcription_id)

    # --- Callbacks from processing tasks ---
    async def process_transcription_result(
        self,
        transcription_id: UUID,
        media_id: UUID,
        result_data: Dict[str, Any],
        provider: str,
        success: bool,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Handles the result of an asynchronous transcription task."""
        transcription = await self._repo.get_by_id(transcription_id)
        if not transcription:
            self._logger.error(
                "transcription.process_result.not_found", transcription_id=str(transcription_id)
            )
            return

        original_status = transcription.status
        if success:
            transcription.mark_as_completed(result_data)
        else:
            transcription.mark_as_failed(error_message or "Unknown error")

        await self._repo.save(transcription)
        
        self._logger.log_operation(
            operation="process_transcription_result",
            media_id=str(media_id),
            transcription_id=str(transcription_id),
            status="COMPLETED" if success else "FAILED",
            original_status=original_status.value,
        )
        self._metrics.set_context(str(media_id))
        await self._metrics.record_operation(
            operation="process_transcription_result",
            provider=provider,
            success=success,
            status=transcription.status.value,
            duration=result_data.get("duration", 0),
            input_audio_length_seconds=result_data.get("input_audio_length_seconds", 0.0),
            output_text_length_chars=len(transcription.text),
        )

        if self._event_bus:
            if success:
                await self._event_bus.publish(
                    TranscriptionCompleted(
                        media_id=media_id,
                        transcription_id=transcription_id,
                        user_id=transcription.media_id,  # Assuming media_id has user_id, will need to fetch media for actual user_id
                        language=transcription.language,
                        text_content=transcription.text,
                        metadata={
                            "provider": provider,
                            "confidence": transcription.confidence_score,
                            "correlation_id": correlation_id,
                            "summarization_provider": result_data.get("summarization_provider"),
                            "sentiment_provider": result_data.get("sentiment_provider"),
                            "topic_modeling_provider": result_data.get("topic_modeling_provider"),
                        },
                    )
                )
            else:
                await self._event_bus.publish(
                    TranscriptionFailed(
                        media_id=media_id,
                        transcription_id=transcription_id,
                        user_id=transcription.media_id, # Assuming media_id has user_id
                        error_message=error_message,
                        provider=provider,
                        correlation_id=correlation_id,
                    )
                )

    async def reprocess_transcription(self, command: ReprocessTranscriptionCommand) -> Dict[str, Any]:
        """Reprocesses a transcription."""
        # Find the media associated with the transcription
        # Needs to fetch media to get file_path and storage_provider
        media = await self._media_queries.get_media(GetTranscriptionByMediaIdQuery(media_id=command.media_id))
        if not media:
            raise ResourceNotFoundError("Media", str(command.media_id))
        
        # Need to check user permissions if required, but AdminService usually handles it.
        # For a user to reprocess, their user_id must match media.user_id.

        # Use the existing request_transcription_generation with new command
        return await self.request_transcription_generation(
            RequestTranscriptionCommand(
                media_id=command.media_id,
                file_path=media.original_file_path,
                storage_provider=media.storage_provider,
                transcription_provider=command.provider or media.transcription_provider,
                language=command.language or media.language,
                file_size_bytes=media.file_size,
                summarization_provider=media.summarization_provider,
                sentiment_provider=media.sentiment_provider,
                topic_modeling_provider=media.topic_modeling_provider,
            )
        )
