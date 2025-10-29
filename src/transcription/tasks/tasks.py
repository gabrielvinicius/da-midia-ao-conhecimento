"""Transcription Celery task resolved via DI container using TranscriptionContainer.

Performs the actual transcription (download + recognize + persist).
"""
from __future__ import annotations

import asyncio
from typing import Optional
from uuid import UUID

import structlog
from celery import shared_task

from src.shared.infrastructure.database import get_db
from src.transcription.bootstrap import TranscriptionContainer
from src.transcription.domain.transcription import Transcription
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str = "en",
) -> Optional[str]:
    try:
        return asyncio.run(
            _run_transcription(media_id, file_path, storage_provider, transcription_provider, language)
        )
    except Exception as e:
        logger.error(
            "transcription.task_failed",
            media_id=media_id,
            error=str(e),
            exc_info=True,
        )
        return None


async def _run_transcription(
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    language: str,
) -> Optional[str]:
    media_uuid = UUID(media_id)
    async for db in get_db():
        container = TranscriptionContainer(db=db)

        repo: TranscriptionRepository = container.transcription_repository()
        storage = container.storage_service()
        recognizer = container.speech_recognizer()
        logger.info(
            "transcription.task.start",
            media_id=media_id,
            provider=transcription_provider,
            language=language,
        )

        transcription = await repo.get_by_media_id(media_uuid)
        if transcription is None:
            transcription = Transcription(
                media_id=media_uuid,
                provider=transcription_provider,
            )
            transcription.process()
            await repo.add(transcription)

        try:
            audio_bytes = await storage.download_file(file_path)
            result_payload = await recognizer.transcribe(audio_bytes, language=language)

            transcription.mark_as_completed(result_payload)
            await repo.update(transcription)
            await db.commit()

            logger.info(
                "transcription.task.completed",
                media_id=media_id,
                transcription_id=str(transcription.id),
            )
            return str(transcription.id)
        except Exception as exc:
            logger.error(
                "transcription.task.error",
                media_id=media_id,
                error=str(exc),
                exc_info=True,
            )
            transcription.mark_as_failed(str(exc))
            await repo.update(transcription)
            await db.commit()
            raise
