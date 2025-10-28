"""Celery tasks responsible for executing background sentiment analysis."""

from __future__ import annotations

import asyncio
from typing import Optional

from celery import shared_task

from src.sentiment_analysis.application.commands.analyze_sentiment_command import (
    AnalyzeSentimentCommand,
)
from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.sentiment_analysis.infrastructure.dependencies import (
    create_sentiment_analysis_service,
)
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.shared.events.event_bus import get_event_bus
from src.shared.infrastructure.database import get_db
from src.transcription.application.queries.transcription_queries import (
    TranscriptionQueries,
)
from src.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def analyze_sentiment_task(
    self,
    transcription_id: str,
    text_content: str,
    provider: str = "huggingface",
    model: Optional[str] = None,
) -> Optional[str]:
    """Entry point for asynchronous sentiment analysis execution."""

    return asyncio.run(
        _execute_sentiment_analysis(
            transcription_id=transcription_id,
            text_content=text_content,
            provider=provider,
            model=model,
        )
    )


async def _execute_sentiment_analysis(
    *,
    transcription_id: str,
    text_content: str,
    provider: str,
    model: Optional[str],
) -> Optional[str]:
    _ = text_content  # Provided for compatibility with event payloads
    async for session in get_db():
        service = await create_sentiment_analysis_service(session)
        repository = SentimentAnalysisRepository(session)
        event_bus = get_event_bus()
        transcription_repository = TranscriptionRepository(session)
        transcription_queries = TranscriptionQueries(transcription_repository)

        handler = AnalyzeSentimentCommandHandler(
            sentiment_service=service,
            analysis_repository=repository,
            transcription_queries=transcription_queries,
            event_bus=event_bus,
            connection_manager=None,
            metrics_service=None,
        )

        command = AnalyzeSentimentCommand(
            transcription_id=transcription_id,
            provider=provider,
            model=model,
        )

        analysis = await handler.handle(command)
        return analysis.id

    return None


__all__ = ["analyze_sentiment_task"]

