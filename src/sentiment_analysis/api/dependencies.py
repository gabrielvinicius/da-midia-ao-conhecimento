from typing import Annotated
from fastapi import Depends, Request

from src.media_management.application.queries.media_queries import MediaQueries
from src.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_sentiment_analysis_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> SentimentAnalysisService:
    return modules.sentiment_analysis.service


def get_sentiment_analysis_repository(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> SentimentAnalysisRepository:
    return modules.sentiment_analysis.repository


def get_media_queries(request: Request) -> MediaQueries:
    return request.app.state.modules.media_management.queries


__all__ = [
    "get_media_queries",
    "get_sentiment_analysis_service",
    "get_sentiment_analysis_repository",
]
