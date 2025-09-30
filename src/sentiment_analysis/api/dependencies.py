# src/sentiment_analysis/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.sentiment_analysis.application.queries.analysis_queries import AnalysisQueries

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_analysis_queries(container: Annotated[dict, Depends(get_container)]) -> AnalysisQueries:
    return container["analysis_queries"]
