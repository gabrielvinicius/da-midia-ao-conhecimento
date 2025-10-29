from __future__ import annotations

import asyncio
from typing import Optional
from uuid import UUID

import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.summarization.bootstrap import (
    create_summarization_container,
    build_summarization_module,
)
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def run_text_analysis_task(self, media_id: str, text_content: Optional[str] = None) -> Optional[str]:
    """Run downstream text analysis (e.g., summarization) for a media.

    This task is resilient to the transcription not being ready yet: if
    no text is available it raises to trigger an automatic retry.
    Returns the summary ID on success (when available).
    """
    try:
        return asyncio.run(_run_analysis(media_id, text_content=text_content))
    except Exception as exc:  # noqa: BLE001
        logger.warning("text_analysis.retrying_or_failed", media_id=media_id, error=str(exc), exc_info=True)
        raise


async def _run_analysis(media_id: str, text_content: Optional[str] = None) -> Optional[str]:
    media_uuid = UUID(media_id)
    async for db in get_db():
        if not isinstance(db, AsyncSession):
            raise TypeError("Expected AsyncSession from get_db()")

        # Prefer explicit text if provided, otherwise wait for transcription
        transcription = None
        if not text_content:
            transcription_repo = TranscriptionRepository(db)
            transcription = await transcription_repo.get_by_media_id(media_uuid)
            if transcription is None or not getattr(transcription, "text", "").strip():
                # Trigger retry via exception; Celery will back off and re-run
                raise RuntimeError("Transcription not ready yet for media")
            text_content = transcription.text

        # Setup summarization dependencies and execute
        container = create_summarization_container(session=db)
        module = await build_summarization_module(container)

        summary = await module.service.generate_summary(
            media_id=media_uuid,
            text_content=text_content,
            provider="builtin",
            options=None,
        )

        logger.info("text_analysis.summary_completed", media_id=media_id, summary_id=str(summary.id))

        # Optional: chain more analyses
        try:
            from src.sentiment_analysis.tasks.analysis_tasks import analyze_sentiment_task
            transcription_id = str(getattr(transcription, "id", "")) if transcription else ""
            if transcription_id:
                analyze_sentiment_task.delay(
                    transcription_id=transcription_id,
                    text_content=text_content,
                    provider="huggingface",
                    model=None,
                )
        except Exception as e:
            logger.warning("text_analysis.sentiment_dispatch_failed", error=str(e))

        try:
            from src.topic_modeling.tasks.topic_modeling_tasks import analyze_topics_task

            analyze_topics_task.delay(
                media_id=str(media_uuid),
                text_content=text_content,
                provider="sklearn_lda",
                language="en",
                options=None,
            )
        except Exception as e:
            logger.warning("text_analysis.topic_modeling_dispatch_failed", error=str(e))

        return str(summary.id)
