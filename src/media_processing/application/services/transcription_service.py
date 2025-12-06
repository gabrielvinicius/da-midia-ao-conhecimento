# src/transcription/application/transcription_service.py
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.domain.model import Transcription
from src.shared.infrastructure.settings import settings
from src.shared.infrastructure.event_bus import SupportsEventBus
from src.media_processing.application.schemas import TranscriptionTaskPayload

if TYPE_CHECKING:
    from src.media_management.application.queries.media_queries import MediaQueries

logger = structlog.get_logger(__name__)

DEFAULT_SUMMARIZATION_PROVIDER = settings.summarization_default_provider
DEFAULT_SENTIMENT_PROVIDER = "builtin"
DEFAULT_TOPIC_PROVIDER = "sklearn_lda"


class TranscriptionService:
    """Application service for orchestrating transcription operations."""

    def __init__(
        self,
        transcription_repo: Any,
        task_scheduler: Any,
        transcription_logger: Any,
        transcription_metrics: Any,
        storage_service: Any,
        speech_recognizer_factory: Callable[[str], Any] | None,
        *,
        media_queries: "MediaQueries" | None = None,
        event_bus: SupportsEventBus | None = None,
        dispatcher: Any | None = None,
    ):
        self.transcription_repo = transcription_repo
        self.task_scheduler = task_scheduler
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics
        self.storage_service = storage_service
        self._speech_recognizer_factory = speech_recognizer_factory
        self._media_queries = media_queries
        self._event_bus = event_bus
        self._dispatcher = dispatcher

    async def request_transcription_generation(
        self,
        *,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: Optional[int] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule a transcription task via the scheduler."""
        
        payload = TranscriptionTaskPayload(
            media_id=media_id,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language,
            file_size_bytes=file_size_bytes or 0,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
        )
        
        if hasattr(self.task_scheduler, 'schedule_transcription_task'):
             result = await self.task_scheduler.schedule_transcription_task(**payload.model_dump(mode="json"))
        elif hasattr(self.task_scheduler, 'schedule_transcription'):
             result = self.task_scheduler.schedule_transcription(payload.model_dump(mode="json"))
        else:
             raise RuntimeError(f"Scheduler {type(self.task_scheduler)} missing schedule method")

        return {
            "success": True,
            "media_id": str(media_id),
            "message": "Transcription scheduled",
            "task_id": result.get("task_id") if isinstance(result, dict) else None
        }

    async def get_transcription_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its associated media ID."""
        lookup = getattr(self.transcription_repo, "find_by_media_id", None) or getattr(self.transcription_repo, "get_by_media_id")
        return await lookup(media_id)

    async def get_transcription_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its ID."""
        lookup = getattr(self.transcription_repo, "find_by_id", None) or getattr(self.transcription_repo, "get_by_id")
        return await lookup(transcription_id)

    def process_transcription_job_sync(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> Optional[str]:
        """Execute transcription workflow synchronously for Celery tasks."""
        start_time = time.monotonic()
        success = False
        error: Optional[Exception] = None
        result_payload: Optional[Any] = None

        transcription: Optional[Transcription] = None

        try:
            transcription = self.transcription_repo.get_by_media_id_sync(media_id)
            if transcription is None:
                transcription = Transcription(
                    media_id=media_id,
                    provider=transcription_provider,
                )
                transcription.process()
                transcription = self.transcription_repo.add_sync(transcription)
                if transcription is None:
                    transcription = self.transcription_repo.get_by_media_id_sync(media_id)
            else:
                transcription.provider = transcription_provider
                transcription.process()
                transcription = self.transcription_repo.update_sync(transcription)
                if transcription is None:
                    transcription = self.transcription_repo.get_by_media_id_sync(media_id)
            
            if transcription is None:
                raise RuntimeError(f"Could not create or retrieve transcription for media_id: {media_id}")

            logger.info(
                "transcription_service.job.started_sync",
                media_id=str(media_id),
                provider=transcription_provider,
                language=language,
                storage_provider=storage_provider,
            )

            audio_bytes = self.storage_service.download_file_sync(file_path)

            recognizer = self._resolve_speech_recognizer(transcription_provider)
            requested_language = (language or "auto").lower()

            if hasattr(recognizer, 'transcribe_sync'):
                result_payload = recognizer.transcribe_sync(
                    audio_bytes,
                    language=requested_language,
                )
            else:
                import concurrent.futures

                def run_async():
                    import asyncio

                    return asyncio.run(
                        recognizer.transcribe(audio_bytes, language=requested_language)
                    )

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    result_payload = future.result()

            transcription.mark_as_completed(result_payload)
            transcription = self.transcription_repo.update_sync(transcription)

            effective_language = transcription.language or language

            self._publish_text_content_ready_sync(
                transcription=transcription,
                media_id=media_id,
                language=effective_language,
                storage_provider=storage_provider,
                summarization_provider=summarization_provider,
                sentiment_provider=sentiment_provider,
                topic_modeling_provider=topic_modeling_provider,
            )

            success = True
            logger.info(
                "transcription_service.job.completed_sync",
                media_id=str(media_id),
                transcription_id=str(transcription.id),
            )
            return str(transcription.id)
        except Exception as exc:
            error = exc
            logger.error(
                "transcription_service.job.failed_sync",
                extra={
                    "media_id": str(media_id),
                    "error": str(exc),
                },
                exc_info=True,
            )
            if transcription is not None:
                transcription.mark_as_failed(str(exc))
                self.transcription_repo.update_sync(transcription)
            raise
        finally:
            duration = time.monotonic() - start_time
            if self.transcription_logger is not None:
                if hasattr(self.transcription_logger, 'log_operation_sync'):
                    try:
                        self.transcription_logger.log_operation_sync(
                            operation="process_transcription_job",
                            media_id=str(media_id),
                            provider=transcription_provider,
                            success=success,
                            duration=duration,
                            error=error,
                        )
                    except Exception:
                        logger.warning(
                            "transcription_logger.sync_log_failed",
                            media_id=str(media_id),
                        )

            if self.transcription_metrics is not None:
                text_output = ""
                if success and result_payload is not None:
                    if isinstance(result_payload, dict):
                        text_output = result_payload.get("text", "") or result_payload.get("result", "")
                    elif isinstance(result_payload, str):
                        text_output = result_payload
                        
                if hasattr(self.transcription_metrics, 'record_operation_sync'):
                    try:
                        self.transcription_metrics.record_operation_sync(
                            operation="process_transcription_job",
                            provider=transcription_provider,
                            duration=duration,
                            success=success,
                            input_audio_length_chars=len(text_output),
                        )
                    except Exception:
                        logger.warning(
                            "transcription_metrics.sync_record_failed",
                            media_id=str(media_id),
                        )

    def _publish_text_content_ready_sync(
        self,
        *,
        transcription: Transcription,
        media_id: UUID,
        language: str,
        storage_provider: str,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
    ) -> None:
        """Synchronous version of publishing text content ready event."""
        text_content = (transcription.text or "").strip()
        if not text_content:
            logger.info(
                "transcription_service.text_event_skipped_sync",
                media_id=str(transcription.media_id),
                reason="missing_text",
            )
            return

        metadata = self._build_text_ready_metadata(
            transcription,
            media_id=media_id,
            language=language,
            storage_provider=storage_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_provider=topic_modeling_provider,
        )
        try:
            self._dispatcher.dispatch(
                transcription_id=str(transcription.id),
                media_id=str(transcription.media_id),
                text=text_content,
                metadata=metadata,
                correlation_id=None,
            )
        except Exception as exc:
            logger.warning(
                "transcription_service.text_dispatch_failed",
                media_id=str(transcription.media_id),
                error=str(exc),
            )

    def _build_text_ready_metadata(
        self,
        transcription: Transcription,
        *,
        media_id: UUID,
        language: str,
        storage_provider: str,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        if language:
            metadata["language"] = language

        if storage_provider:
            metadata["storage_provider"] = storage_provider

        metadata["summarization_provider"] = summarization_provider or DEFAULT_SUMMARIZATION_PROVIDER
        metadata["sentiment_provider"] = sentiment_provider or DEFAULT_SENTIMENT_PROVIDER
        metadata["topic_provider"] = topic_provider or DEFAULT_TOPIC_PROVIDER

        return metadata

    def _resolve_speech_recognizer(self, provider: str) -> Any:
        if self._speech_recognizer_factory is None:
            raise RuntimeError("Speech recognizer factory is not configured")

        provider_name = provider or "whisper"
        return self._speech_recognizer_factory(provider_name)

    def get_transcription_by_media_id_sync(
        self,
        media_id: UUID,
    ) -> Optional[Transcription]:
        """Retrieves a transcription by its associated media ID."""
        return self.transcription_repo.get_by_media_id_sync(media_id)

    def get_transcription_by_id_sync(
        self,
        transcription_id: UUID,
    ) -> Optional[Transcription]:
        """Retrieves a transcription by its ID."""
        return self.transcription_repo.get_by_id_sync(transcription_id)