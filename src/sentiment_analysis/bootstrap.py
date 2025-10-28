"""Dependency Injector container for the sentiment analysis module."""
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.sentiment_analysis.application.queries.sentiment_analysis_queries import (
    SentimentAnalysisQueries,
)
from src.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics
from src.sentiment_analysis.infrastructure.sentiment_analyzer import (
    SimpleSentimentAnalyzer,
)
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.shared.events.event_bus import EventBus


class SentimentAnalysisContainer(containers.DeclarativeContainer):
    """Composition root for the sentiment analysis sub-system."""

    db: providers.Dependency[AsyncSession] = providers.Dependency()
    event_bus = providers.Dependency(default=None)
    transcription_queries = providers.Dependency(default=None)
    connection_manager = providers.Dependency(default=None)
    metrics_service = providers.Dependency(default=None)

    repository = providers.Factory(SentimentAnalysisRepository, db=db)
    analyzer = providers.Singleton(SimpleSentimentAnalyzer)
    sentiment_logger = providers.Singleton(StructuredSentimentLogger)
    sentiment_metrics = providers.Singleton(PrometheusSentimentMetrics)

    sentiment_analysis_service = providers.Factory(
        SentimentAnalysisService,
        analyzer=analyzer,
        repository=repository,
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
        event_bus=event_bus,
        connection_manager=connection_manager,
        metrics_service=_handler_metrics,
    )


@dataclass
class SentimentAnalysisModule:
    service: SentimentAnalysisService
    repository: SentimentAnalysisRepository


def build_sentiment_analysis_module(
    session: AsyncSession,
    event_bus: EventBus,
    transcription_queries,
    connection_manager,
    metrics_service,
) -> SentimentAnalysisModule:
    container = SentimentAnalysisContainer(
        db=session,
        event_bus=event_bus,
        transcription_queries=providers.Object(transcription_queries),
        connection_manager=providers.Object(connection_manager),
        metrics_service=providers.Object(metrics_service),
    )

    return SentimentAnalysisModule(
        service=container.sentiment_analysis_service(),
        repository=container.sentiment_analysis_repository(),
    )


__all__ = ["SentimentAnalysisContainer", "SentimentAnalysisModule", "build_sentiment_analysis_module"]
