# src/summarization/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.summarization.bootstrap import SummarizationContainer
from src.summarization.application.summarization_service import SummarizationService
from src.summarization.application.commands.handlers import RequestSummaryCommandHandler, ProcessSummaryCommandHandler

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
