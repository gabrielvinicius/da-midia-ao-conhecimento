# src/summarization/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.summarization.application.summarization_service import SummarizationService
from src.summarization.application.queries.summary_queries import SummaryQueries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries # Added dependency

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_summarization_service(container: Annotated[dict, Depends(get_container)]) -> SummarizationService:
    return container["summarization_service"]

def get_summary_queries(container: Annotated[dict, Depends(get_container)]) -> SummaryQueries:
    return container["summary_queries"]


def get_transcription_queries(container: Annotated[dict, Depends(get_container)]) -> TranscriptionQueries:
    return container["transcription_queries"]
