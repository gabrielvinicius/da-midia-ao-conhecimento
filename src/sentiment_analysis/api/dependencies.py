"""Dependency wiring for sentiment analysis API endpoints."""

from typing import Annotated

from fastapi import Depends, Request

from src.media_management.application.queries.media_queries import MediaQueries
from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.sentiment_analysis.application.queries.sentiment_analysis_queries import (
    SentimentAnalysisQueries,
)
from src.sentiment_analysis.bootstrap import SentimentAnalysisContainer


def get_sentiment_analysis_container(
    request: Request,
) -> SentimentAnalysisContainer:
    """Expose the configured container stored in the FastAPI application state."""

    return request.app.state.container["sentiment_analysis_container"]


def get_sentiment_analysis_queries(
    container: Annotated[
        SentimentAnalysisContainer, Depends(get_sentiment_analysis_container)
    ]
) -> SentimentAnalysisQueries:
    """Retrieve the queries object from the dependency container."""

    return container.sentiment_analysis_queries()


def get_media_queries(request: Request) -> MediaQueries:
    """Expose media queries stored in the shared application container."""

    return request.app.state.container["media_queries"]


def get_analyze_sentiment_command_handler(
    container: Annotated[
        SentimentAnalysisContainer, Depends(get_sentiment_analysis_container)
    ]
) -> AnalyzeSentimentCommandHandler:
    """Retrieve the command handler configured in the container."""

    return container.analyze_sentiment_command_handler()


__all__ = [
    "get_media_queries",
    "get_analyze_sentiment_command_handler",
    "get_sentiment_analysis_container",
    "get_sentiment_analysis_queries",
]

