from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_management.api.dependencies import get_media_queries
from src.transcription.api.dependencies import get_transcription_queries
from src.summarization.application.commands.handlers import (
    ProcessSummaryCommandHandler,
    RequestSummaryCommandHandler,
)
from src.summarization.application.summarization_service import SummarizationService


class SummarizationDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class SummarizationDependencies:
    service: SummarizationService
    request_handler: RequestSummaryCommandHandler
    process_handler: ProcessSummaryCommandHandler


def get_summarization_dependencies() -> SummarizationDependencies:
    raise SummarizationDependenciesNotConfigured(
        "Summarization dependencies are not configured. Register providers in the lifespan handler."
    )


SummarizationDeps = Annotated[
    SummarizationDependencies, Depends(get_summarization_dependencies)
]


def get_summarization_service(
    deps: SummarizationDeps,
) -> SummarizationService:
    return deps.service


def get_request_summary_command_handler(
    deps: SummarizationDeps,
) -> RequestSummaryCommandHandler:
    return deps.request_handler


def get_process_summary_command_handler(
    deps: SummarizationDeps,
) -> ProcessSummaryCommandHandler:
    return deps.process_handler


__all__ = [
    "SummarizationDependencies",
    "SummarizationDependenciesNotConfigured",
    "get_media_queries",
    "get_process_summary_command_handler",
    "get_request_summary_command_handler",
    "get_summarization_dependencies",
    "get_summarization_service",
    "get_transcription_queries",
]
