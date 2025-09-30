# src/sentiment_analysis/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .application.queries.sentiment_analysis_queries import SentimentAnalysisQueries
from .infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository

def bootstrap_sentiment_analysis_module(db_session: AsyncSession) -> Dict[str, Any]:
    """Constructs and returns the query services for the sentiment analysis module."""
    repository = SentimentAnalysisRepository(db=db_session)
    queries = SentimentAnalysisQueries(repository=repository)

    return {
        "sentiment_analysis_repository": repository,
        "sentiment_analysis_queries": queries,
    }
