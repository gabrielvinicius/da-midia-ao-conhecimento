from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_management.api.dependencies import get_media_queries
from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)


class SentimentDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class SentimentDependencies:
    service: SentimentAnalysisService
    repository: SentimentAnalysisRepository


def get_sentiment_dependencies() -> SentimentDependencies:
    raise SentimentDependenciesNotConfigured(
        "Sentiment analysis dependencies are not configured. Register providers in the lifespan handler."
    )


SentimentDeps = Annotated[SentimentDependencies, Depends(get_sentiment_dependencies)]


def get_sentiment_analysis_service(
    deps: SentimentDeps,
) -> SentimentAnalysisService:
    return deps.service


def get_sentiment_analysis_repository(
    deps: SentimentDeps,
) -> SentimentAnalysisRepository:
    return deps.repository


__all__ = [
    "SentimentDependencies",
    "SentimentDependenciesNotConfigured",
    "get_media_queries",
    "get_sentiment_analysis_repository",
    "get_sentiment_analysis_service",
    "get_sentiment_dependencies",
]
