"""Dependency Injector container for the sentiment analysis module."""
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.text_analysis.sentiment_analysis.application.queries.sentiment_analysis_queries import (
    SentimentAnalysisQueries,
)
from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.text_analysis.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analyzer import (
    SimpleSentimentAnalyzer,
)
from src.text_analysis.application.services import TextAnalysisService


class SentimentAnalysisContainer(containers.DeclarativeContainer):
    """Composition root for the sentiment analysis sub-system."""

    db: providers.Dependency[AsyncSession] = providers.Dependency()
    transcription_queries = providers.Dependency(default=None)
    connection_manager = providers.Dependency(default=None)
    metrics_service = providers.Dependency(default=None)
    text_analysis_service = providers.Dependency(default=None)

    repository = providers.Factory(SentimentAnalysisRepository, db=db)
    analyzer = providers.Singleton(SimpleSentimentAnalyzer)
    sentiment_logger = providers.Singleton(StructuredSentimentLogger)
    sentiment_metrics = providers.Singleton(PrometheusSentimentMetrics)

    sentiment_analysis_service = providers.Factory(
        SentimentAnalysisService,
        analyzer=analyzer,
        repository=repository,
        text_analysis_service=text_analysis_service,
        logger=sentiment_logger,
        metrics=sentiment_metrics,
    )

    sentiment_analysis_repository = repository
    sentiment_analysis_queries = providers.Factory(
        SentimentAnalysisQueries, repository=repository
    )

    _handler_metrics = providers.Callable(
        lambda provided, fallback: provided if provided is not None else fallback,
        metrics_service,
        sentiment_metrics,
    )

    analyze_sentiment_command_handler = providers.Factory(
        AnalyzeSentimentCommandHandler,
        sentiment_service=sentiment_analysis_service,
        analysis_repository=repository,
        transcription_queries=transcription_queries,
        connection_manager=connection_manager,
        metrics_service=_handler_metrics,
    )


@dataclass
class SentimentAnalysisModule:
    service: SentimentAnalysisService
    repository: SentimentAnalysisRepository


async def build_sentiment_analysis_module(
    session: AsyncSession,
    transcription_queries,
    connection_manager,
    metrics_service,
    text_analysis_service: TextAnalysisService,
) -> SentimentAnalysisModule:
    container = SentimentAnalysisContainer(
        transcription_queries=providers.Object(transcription_queries),
        connection_manager=providers.Object(connection_manager),
        metrics_service=providers.Object(metrics_service),
        text_analysis_service=providers.Object(text_analysis_service),
    )
    container.db.override(providers.Object(session))

    module = SentimentAnalysisModule(
        service=container.sentiment_analysis_service(),
        repository=container.sentiment_analysis_repository(),
    )
    # EventBus handler registration disabled; use Celery-triggered workflows
    return module


__all__ = ["SentimentAnalysisContainer", "SentimentAnalysisModule", "build_sentiment_analysis_module"]
