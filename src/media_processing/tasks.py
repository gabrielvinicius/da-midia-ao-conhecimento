# src/media_processing/tasks.py
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain.enums import MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.shared.infrastructure.database import get_db

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_media_task(self, media_id: str) -> None:
    """Celery entry point to process a media item by ID.

    Delegates to existing, specialized tasks based on media type.
    Schedules transcription for AUDIO/VIDEO and defers downstream text
    analysis to dedicated tasks (see src.text_analysis.tasks).
    """
    try:
        return asyncio.run(_route_processing(media_id))
    except Exception as exc:  # noqa: BLE001 - capture for logging
        logger.error("media_processing.failed", media_id=media_id, error=str(exc), exc_info=True)
        raise


async def _route_processing(media_id: str) -> None:
    async for db in get_db():
        if not isinstance(db, AsyncSession):  # defensive
            raise TypeError("Expected AsyncSession from get_db()")

        repo = MediaRepository(db=db)
        media = await repo.get_by_id(UUID(media_id))
        if media is None:
            raise ValueError(f"Media not found: {media_id}")

        logger.info(
            "media_processing.route",
            media_id=str(media.id),
            media_type=str(media.media_type),
            storage_provider=media.storage_provider,
        )

        # AUDIO/VIDEO -> transcription pipeline
        if media.media_type in (MediaType.AUDIO, MediaType.VIDEO):
            from src.transcription.tasks.tasks import process_transcription_task

            process_transcription_task.delay(
                media_id=str(media.id),
                file_path=media.original_file_path,
                storage_provider=media.storage_provider,
                transcription_provider=media.transcription_provider or "fastwhisper",
                language=media.language or "en",
            )

            # Chain text analysis that will retry until transcription is ready
            try:
                from src.text_analysis.tasks import run_text_analysis_task

                run_text_analysis_task.delay(media_id=str(media.id))
            except Exception as chain_exc:  # optional chaining
                logger.warning("media_processing.chain_text_analysis_failed", error=str(chain_exc))

            return

        # TEXT -> attempt extraction locally, then analyze
        if media.media_type is MediaType.TEXT:
            try:
                # Best-effort: read file bytes if path exists (local provider)
                from pathlib import Path
                from src.shared.infrastructure.unified_extractors import extract_text_from_file

                file_path = Path(media.original_file_path)
                text_content: str | None = None
                if file_path.exists():
                    data = await asyncio.to_thread(file_path.read_bytes)
                    result = await extract_text_from_file(data, media.filename or file_path.name)
                    text_content = result.text if getattr(result, "success", False) else None

                from src.text_analysis.tasks import run_text_analysis_task
                run_text_analysis_task.delay(media_id=str(media.id), text_content=text_content)
                return
            except Exception as exc:
                logger.error("media_processing.text_analysis_dispatch_failed", error=str(exc))
                raise

        raise ValueError(f"Unsupported media type: {media.media_type}
                         ")
