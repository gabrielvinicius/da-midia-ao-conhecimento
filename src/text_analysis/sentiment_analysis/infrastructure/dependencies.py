"""Factory helpers for wiring sentiment analysis infrastructure."""

from __future__ import annotations

from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.sentiment_analysis.infrastructure.logging import StructuredSentimentLogger
from src.text_analysis.sentiment_analysis.infrastructure.metrics import PrometheusSentimentMetrics
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analyzer import (
    SimpleSentimentAnalyzer,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)


class SentimentServiceFactory:
    """Callable factory that instantiates ``SentimentAnalysisService`` objects."""

    def __init__(self) -> None:
        self._analyzer = SimpleSentimentAnalyzer()
        self._logger = StructuredSentimentLogger()
        self._metrics = PrometheusSentimentMetrics()

    def __call__(self, db: AsyncSession) -> SentimentAnalysisService:
        repository = SentimentAnalysisRepository(db)
        return SentimentAnalysisService(
            analyzer=self._analyzer,
            repository=repository,
            logger=self._logger,
            metrics=self._metrics,
        )


def get_sentiment_service_factory() -> SentimentServiceFactory:
    """Expose a factory compatible with the FastAPI composition root."""

    return SentimentServiceFactory()


async def create_sentiment_analysis_service(
    db: AsyncSession,
) -> SentimentAnalysisService:
    """Create a fully-wired ``SentimentAnalysisService`` instance."""

    factory = get_sentiment_service_factory()
    return factory(db)


SentimentServiceFactoryCallable = Callable[[AsyncSession], SentimentAnalysisService]

__all__ = [
    "SentimentServiceFactory",
    "SentimentServiceFactoryCallable",
    "create_sentiment_analysis_service",
    "get_sentiment_service_factory",
]

