# src/sentiment_analysis/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .application.queries.analysis_queries import AnalysisQueries
from .infrastructure.analysis_repository import AnalysisRepository

def bootstrap_sentiment_analysis_module(db_session: AsyncSession) -> Dict[str, Any]:
    """Constructs and returns the services for the sentiment_analysis module."""
    analysis_repository = AnalysisRepository(db=db_session)
    analysis_queries = AnalysisQueries(analysis_repository=analysis_repository)

    return {
        "analysis_repository": analysis_repository,
        "analysis_queries": analysis_queries,
    }
