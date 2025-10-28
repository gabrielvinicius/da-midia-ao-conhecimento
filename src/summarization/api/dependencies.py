from typing import Annotated
from fastapi import Depends, Request

from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries import TranscriptionQueries
from src.summarization.application.commands.handlers import (
    ProcessSummaryCommandHandler,
    RequestSummaryCommandHandler,
)
from src.summarization.application.summarization_service import SummarizationService
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_summarization_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> SummarizationService:
    return modules.summarization.service


def get_request_summary_command_handler(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> RequestSummaryCommandHandler:
    return modules.summarization.request_handler


def get_process_summary_command_handler(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> ProcessSummaryCommandHandler:
    return modules.summarization.process_handler


def get_media_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> MediaQueries:
    return modules.media_management.queries


def get_transcription_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> TranscriptionQueries:
    return modules.transcription.queries
