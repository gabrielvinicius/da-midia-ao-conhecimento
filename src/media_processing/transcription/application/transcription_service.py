# src/transcription/application/transcription_service.py
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from src.media_processing.transcription.domain.transcription import Transcription
from src.shared.event_bus import SupportsEventBus
from src.shared.events.domain_events import TextContentReady

if TYPE_CHECKING:
    from src.media_management.application.queries.media_queries import MediaQueries

logger = structlog.get_logger(__name__)

DEFAULT_SUMMARIZATION_PROVIDER = "builtin"
DEFAULT_SENTIMENT_PROVIDER = "builtin"
DEFAULT_TOPIC_PROVIDER = "bertopic"


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
        db_session: Session,  # Changed to sync session
        *,
        media_queries: "MediaQueries" | None = None,
        event_bus: SupportsEventBus | None = None,
    ):
        self.transcription_repo = transcription_repo
        self.task_scheduler = task_scheduler
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics
        self.storage_service = storage_service
        self._speech_recognizer_factory = speech_recognizer_factory
        self.db_session = db_session  # This should be a sync session for Celery
        self._media_queries = media_queries
        self._event_bus = event_bus

    def process_transcription_job_sync(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
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
                # Ensure transcription is not None after adding
                if transcription is None:
                    # If add_sync didn't return the object, fetch it again by media_id
                    transcription = self.transcription_repo.get_by_media_id_sync(media_id)
            else:
                # Update the provider if it changed
                transcription.provider = transcription_provider
                transcription.process()  # Mark as processing again
                transcription = self.transcription_repo.update_sync(transcription)
                # Ensure transcription is not None after updating
                if transcription is None:
                    # If update_sync didn't return the object, fetch it again by media_id
                    transcription = self.transcription_repo.get_by_media_id_sync(media_id)
            
            # Double check that transcription is not None before proceeding
            if transcription is None:
                raise RuntimeError(f"Could not create or retrieve transcription for media_id: {media_id}")

            logger.info(
                "transcription_service.job.started_sync",
                media_id=str(media_id),
                provider=transcription_provider,
                language=language,
                storage_provider=storage_provider,
            )

            # Download file synchronously using the storage service
            audio_bytes = self.storage_service.download_file_sync(file_path)

            recognizer = self._resolve_speech_recognizer(transcription_provider)
            
            # Use sync transcription if available, otherwise try async in new thread
            if hasattr(recognizer, 'transcribe_sync'):
                result_payload = recognizer.transcribe_sync(audio_bytes, language=language)
            else:
                import concurrent.futures
                def run_async():
                    import asyncio
                    return asyncio.run(recognizer.transcribe(audio_bytes, language=language))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    result_payload = future.result()

            transcription.mark_as_completed(result_payload)
            transcription = self.transcription_repo.update_sync(transcription)
            self.db_session.commit()

            # Publish event synchronously if possible
            self._publish_text_content_ready_sync(
                transcription=transcription,
                media_id=media_id,
                language=language,
                storage_provider=storage_provider,
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
                self.db_session.commit()
            raise
        finally:
            duration = time.monotonic() - start_time
            if self.transcription_logger is not None:
                # Use sync logging if available
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
                        
                # Use sync metrics if available
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
    ) -> None:
        """Synchronous version of publishing text content ready event."""
        if self._event_bus is None:
            return

        text_content = (transcription.text or "").strip()
        if not text_content:
            logger.info(
                "transcription_service.text_event_skipped_sync",
                media_id=str(transcription.media_id),
                reason="missing_text",
            )
            return

        # Build metadata for the event
        metadata = self._build_text_ready_metadata(transcription, media_id=media_id, language=language, storage_provider=storage_provider)
        event = TextContentReady(
            media_id=str(transcription.media_id),
            transcription_id=str(transcription.id),
            text_content=text_content,
            metadata=metadata,
        )

        try:
            # Use sync publishing if available, otherwise use async in new thread
            if hasattr(self._event_bus, 'publish_sync'):
                self._event_bus.publish_sync(event)
            else:
                import concurrent.futures
                def run_async():
                    import asyncio
                    return asyncio.run(self._event_bus.publish(event))

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    future.result()  # Wait for the event to be published
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "transcription_service.text_event_failed_sync",
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
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}

        if language:
            metadata["language"] = language

        if storage_provider:
            metadata["storage_provider"] = storage_provider

        metadata["summarization_provider"] = DEFAULT_SUMMARIZATION_PROVIDER
        metadata["sentiment_provider"] = DEFAULT_SENTIMENT_PROVIDER
        metadata["topic_provider"] = DEFAULT_TOPIC_PROVIDER

        # Add other metadata as needed
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