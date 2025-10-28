# src/summarization/api/dependencies.py
from typing import Annotated

from fastapi import Depends, Request
from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries import TranscriptionQueries
from src.summarization.application.commands.handlers import (
    ProcessSummaryCommandHandler,
    RequestSummaryCommandHandler,
)
from src.summarization.application.summarization_service import SummarizationService
from src.summarization.bootstrap import SummarizationContainer

def get_summarization_container(
    request: Request
) -> SummarizationContainer:
    """Get the summarization dependency injection container from request."""
    return request.app.state.container["summarization_container"]

def get_summarization_service(
    container: Annotated[SummarizationContainer, Depends(get_summarization_container)]
) -> SummarizationService:
    """Get summarization service dependency."""
    return container.summarization_service()

def get_request_summary_command_handler(
    container: Annotated[SummarizationContainer, Depends(get_summarization_container)]
) -> RequestSummaryCommandHandler:
    """Get request summary command handler dependency."""
    return container.request_summary_command_handler()

def get_process_summary_command_handler(
    container: Annotated[SummarizationContainer, Depends(get_summarization_container)]
) -> ProcessSummaryCommandHandler:
    """Get process summary command handler dependency."""
    return container.process_summary_command_handler()


def get_media_queries(request: Request) -> MediaQueries:
    """Expose media queries stored in the application container."""

    return request.app.state.container["media_queries"]


def get_transcription_queries(request: Request) -> TranscriptionQueries:
    """Expose transcription queries stored in the application container."""

    return request.app.state.container["transcription_queries"]
