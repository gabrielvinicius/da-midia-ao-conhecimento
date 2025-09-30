# src/sentiment_analysis/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.sentiment_analysis.application.queries.sentiment_analysis_queries import SentimentAnalysisQueries

# --- Query Getter ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_sentiment_analysis_queries(container: Annotated[dict, Depends(get_container)]) -> SentimentAnalysisQueries:
    return container["sentiment_analysis_queries"]
