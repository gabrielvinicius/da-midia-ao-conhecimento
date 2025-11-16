"""Celery tasks responsible for executing background sentiment analysis."""

from __future__ import annotations

from typing import Optional

from celery import shared_task

from src.media_processing.transcription.application.queries.transcription_queries import (
    TranscriptionQueries,
)
from src.media_processing.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)
from src.shared.infrastructure.database import get_sync_db
from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command import (
    AnalyzeSentimentCommand,
)
from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.text_analysis.sentiment_analysis.infrastructure.dependencies import (
    create_sentiment_analysis_service_sync,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
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
    # Use synchronous database session in Celery worker
    with get_sync_db() as session:
        return _execute_sentiment_analysis_sync(
            transcription_id=transcription_id,
            text_content=text_content,
            provider=provider,
            model=model,
            session=session,
        )


def _execute_sentiment_analysis_sync(
    *,
    transcription_id: str,
    text_content: str,
    provider: str,
    model: Optional[str],
    session,
) -> Optional[str]:
    _ = text_content  # Provided for compatibility with event payloads
    
    service = create_sentiment_analysis_service_sync(session)
    repository = SentimentAnalysisRepository(session)  # This should work with sync session now
    transcription_repository = TranscriptionRepository(session)  # This should work with sync session now
    transcription_queries = TranscriptionQueries(transcription_repository)

    handler = AnalyzeSentimentCommandHandler(
        sentiment_service=service,
        analysis_repository=repository,
        transcription_queries=transcription_queries,
        connection_manager=None,
        metrics_service=None,
    )

    command = AnalyzeSentimentCommand(
        transcription_id=transcription_id,
        provider=provider,
        model=model,
    )

    # Use sync method if available, otherwise implement async-to-sync conversion
    try:
        if hasattr(handler, 'handle_sync'):
            analysis = handler.handle_sync(command)
        else:
            # Fallback: use async method with new event loop
            import asyncio
            try:
                # Check if handler has a sync method, otherwise try async
                if hasattr(handler, 'handle_sync'):
                    analysis = handler.handle_sync(command)
                else:
                    import asyncio
                    try:
                        analysis = asyncio.run(handler.handle(command))
                    except RuntimeError:
                        # If there's already an event loop running, use thread-based approach
                        import concurrent.futures
                        def run_async():
                            import asyncio
                            return asyncio.run(handler.handle(command))
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_async)
                            analysis = future.result()
            except RuntimeError:
                # If there's already an event loop, use thread-based approach
                import concurrent.futures
                def run_async():
                    return asyncio.run(handler.handle(command))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    analysis = future.result()
        return str(analysis.id) if analysis and hasattr(analysis, 'id') else None
    except Exception as e:
        # Log the error but let Celery handle retries
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error(
            "sentiment_analysis.execution_failed",
            transcription_id=transcription_id,
            error=str(e),
            exc_info=True,
        )
        raise

__all__ = ["analyze_sentiment_task"]

