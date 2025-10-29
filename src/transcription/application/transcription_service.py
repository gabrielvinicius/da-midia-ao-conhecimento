# src/transcription/application/transcription_service.py
from typing import Dict, Any, Optional
from uuid import UUID

import structlog

from src.transcription.domain.transcription import Transcription

logger = structlog.get_logger(__name__)


class TranscriptionService:
    """Application service for orchestrating transcription operations."""

    def __init__(
        self,
            transcription_repo: Any,
            task_scheduler: Any,
            transcription_logger: Any,
            transcription_metrics: Any,
    ):
        self.transcription_repo = transcription_repo
        self.task_scheduler = task_scheduler
        self.transcription_logger = transcription_logger
        self.transcription_metrics = transcription_metrics

    async def request_transcription_generation(self, media_id: UUID, file_path: str, storage_provider: str, transcription_provider: str, language: str) -> Dict[str, Any]:
        """Requests the generation of a transcription for a given media item."""
        logger.info(
            "transcription_service.request_transcription_generation",
            media_id=str(media_id),
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language
        )
        try:
            # 1. Create a new transcription entity in PENDING state
            new_transcription = Transcription(
                media_id=media_id,
                provider=transcription_provider
            )
            new_transcription.process() # Marcar como processando
            await self.transcription_repo.add(new_transcription)

            # 2. Schedule the transcription task
            task_result = await self.task_scheduler.schedule_transcription_task(
                media_id=str(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language
            )

            logger.info(
                "transcription_service.transcription_generation_scheduled",
                media_id=str(media_id),
                transcription_id=str(new_transcription.id),
                task_id=task_result.get("task_id")
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "transcription_id": str(new_transcription.id),
                "task_id": task_result.get("task_id"),
                "message": "Transcription task scheduled successfully"
            }
        except Exception as e:
            logger.error(
                "transcription_service.request_transcription_generation_failed",
                media_id=str(media_id),
                error=str(e)
            )
            raise

    async def get_transcription_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its associated media ID."""
        return await self.transcription_repo.get_by_media_id(media_id)

    async def get_transcription_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        """Retrieves a transcription by its ID."""
        return await self.transcription_repo.get_by_id(transcription_id)

    async def set_speaker_aliases(self, transcription_id: UUID, aliases: Dict[str, str]) -> Dict[str, Any]:
        """Sets speaker aliases for a transcription."""
        logger.info(
            "transcription_service.set_speaker_aliases",
            transcription_id=str(transcription_id)
        )
        try:
            transcription = await self.transcription_repo.get_by_id(transcription_id)
            if not transcription:
                logger.error("transcription_service.set_speaker_aliases_failed", transcription_id=str(transcription_id), error="Transcription not found")
                raise ValueError(f"Transcription with ID {transcription_id} not found.")

            transcription.set_speaker_aliases(aliases)
            await self.transcription_repo.update(transcription)

            logger.info(
                "transcription_service.speaker_aliases_set",
                transcription_id=str(transcription_id)
            )
            return {
                "success": True,
                "transcription_id": str(transcription_id),
                "message": "Speaker aliases set successfully"
            }
        except Exception as e:
            logger.error(
                "transcription_service.set_speaker_aliases_failed",
                transcription_id=str(transcription_id),
                error=str(e)
            )
            raise
