# src/transcription/application/transcription_service.py
import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_processing.transcription.domain.transcription import Transcription

logger = structlog.get_logger(__name__)


class TranscriptionService:
    """Application service for orchestrating transcription operations."""

    def __init__(
        self,
        transcription_repo: Any,
        task_scheduler: Any,
        transcription_logger: Any,
        transcription_metrics: Any,
        storage_service: Any,
        speech_recognizer: Any,
        db_session: AsyncSession,
    ):
        self.transcription_repo = transcription_repo
        self.task_scheduler = task_scheduler
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics
        self.storage_service = storage_service
        self.speech_recognizer = speech_recognizer
        self.db_session = db_session

    async def request_transcription_generation(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Requests the generation of a transcription for a given media item."""
        logger.info(
            "transcription_service.request_transcription_generation",
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language,
        )
        start_time = time.monotonic()
        success = False
        try:
            # 1. Create a new transcription entity in PENDING state
            new_transcription = Transcription(
                media_id=media_id,
                provider=transcription_provider,
            )
            new_transcription.process()
            await self.transcription_repo.add(new_transcription)

            # 2. Schedule the transcription task
            task_result = await self.task_scheduler.schedule_transcription_task(
                media_id=str(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
                file_size_bytes=file_size_bytes,
            )

            logger.info(
                "transcription_service.transcription_generation_scheduled",
                media_id=str(media_id),
                transcription_id=str(new_transcription.id),
                task_id=task_result.get("task_id"),
            )
            success = True
            return {
                "success": True,
                "media_id": str(media_id),
                "transcription_id": str(new_transcription.id),
                "task_id": task_result.get("task_id"),
                "message": "Transcription task scheduled successfully",
            }
        except Exception as exc:
            logger.error(
                "transcription_service.request_transcription_generation_failed",
                media_id=str(media_id),
                error=str(exc),
            )
            raise
        finally:
            try:
                await self.transcription_metrics.record_operation(
                    operation="request_transcription_generation",
                    provider=transcription_provider,
                    duration=time.monotonic() - start_time,
                    success=success,
                    input_audio_length_seconds=0.0,
                    output_text_length_chars=0,
                )
            except Exception:  # pragma: no cover - metrics best effort
                logger.warning(
                    "transcription_metrics.record_failed",
                    media_id=str(media_id),
                )

    async def process_transcription_job(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
    ) -> Optional[str]:
        """Execute transcription workflow previously held inside the Celery task."""
        start_time = time.monotonic()
        success = False
        error: Optional[Exception] = None
        result_payload: Optional[Any] = None

        transcription: Optional[Transcription] = None

        try:
            transcription = await self.transcription_repo.get_by_media_id(media_id)
            if transcription is None:
                transcription = Transcription(
                    media_id=media_id,
                    provider=transcription_provider,
                )
                transcription.process()
                await self.transcription_repo.add(transcription)

            logger.info(
                "transcription_service.job.started",
                media_id=str(media_id),
                provider=transcription_provider,
                language=language,
                storage_provider=storage_provider,
            )

            audio_bytes = await self.storage_service.download_file(file_path)
            result_payload = await self.speech_recognizer.transcribe(
                audio_bytes, language=language
            )

            transcription.mark_as_completed(result_payload)
            await self.transcription_repo.update(transcription)
            await self.db_session.commit()

            success = True
            logger.info(
                "transcription_service.job.completed",
                media_id=str(media_id),
                transcription_id=str(transcription.id),
            )
            return str(transcription.id)
        except Exception as exc:
            error = exc
            logger.error(
                "transcription_service.job.failed",
                media_id=str(media_id),
                error=str(exc),
                exc_info=True,
            )
            if transcription is not None:
                transcription.mark_as_failed(str(exc))
                await self.transcription_repo.update(transcription)
                await self.db_session.commit()
            raise
        finally:
            duration = time.monotonic() - start_time
            if self.transcription_logger is not None:
                try:
                    await self.transcription_logger.log_operation(
                        operation="process_transcription_job",
                        media_id=str(media_id),
                        provider=transcription_provider,
                        success=success,
                        duration=duration,
                        error=error,
                    )
                except Exception:  # pragma: no cover - logging best effort
                    logger.warning(
                        "transcription_logger.record_failed",
                        media_id=str(media_id),
                    )

            if self.transcription_metrics is not None:
                text_output = ""
                if success and result_payload is not None:
                    if isinstance(result_payload, dict):
                        text_output = result_payload.get("text", "") or ""
                    elif isinstance(result_payload, str):
                        text_output = result_payload
                try:
                    await self.transcription_metrics.record_operation(
                        operation="process_transcription_job",
                        provider=transcription_provider,
                        duration=duration,
                        success=success,
                        input_audio_length_seconds=0.0,
                        output_text_length_chars=len(text_output),
                    )
                except Exception:  # pragma: no cover - metrics best effort
                    logger.warning(
                        "transcription_metrics.record_failed",
                        media_id=str(media_id),
                    )

    async def get_transcription_by_media_id(
        self,
        media_id: UUID,
    ) -> Optional[Transcription]:
        """Retrieves a transcription by its associated media ID."""
        return await self.transcription_repo.get_by_media_id(media_id)

    async def get_transcription_by_id(
        self,
        transcription_id: UUID,
    ) -> Optional[Transcription]:
        """Retrieves a transcription by its ID."""
        return await self.transcription_repo.get_by_id(transcription_id)

    async def set_speaker_aliases(
        self,
        transcription_id: UUID,
        aliases: Dict[str, str],
    ) -> Dict[str, Any]:
        """Sets speaker aliases for a transcription."""
        logger.info(
            "transcription_service.set_speaker_aliases",
            transcription_id=str(transcription_id),
        )
        try:
            transcription = await self.transcription_repo.get_by_id(transcription_id)
            if not transcription:
                logger.error(
                    "transcription_service.set_speaker_aliases_failed",
                    transcription_id=str(transcription_id),
                    error="Transcription not found",
                )
                raise ValueError(
                    f"Transcription with ID {transcription_id} not found."
                )

            transcription.set_speaker_aliases(aliases)
            await self.transcription_repo.update(transcription)

            logger.info(
                "transcription_service.speaker_aliases_set",
                transcription_id=str(transcription_id),
            )
            return {
                "success": True,
                "transcription_id": str(transcription_id),
                "message": "Speaker aliases set successfully",
            }
        except Exception as exc:
            logger.error(
                "transcription_service.set_speaker_aliases_failed",
                transcription_id=str(transcription_id),
                error=str(exc),
            )
            raise
