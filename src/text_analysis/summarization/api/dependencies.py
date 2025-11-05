from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.text_analysis.summarization.application.summarization_service import (
    SummarizationService,
)
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)


class SummarizationDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class SummarizationDependencies:
    service: SummarizationService
    repository: SummarizationRepository


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


def get_summarization_repository(
    deps: SummarizationDeps,
) -> SummarizationRepository:
    return deps.repository


__all__ = [
    "SummarizationDependencies",
    "SummarizationDependenciesNotConfigured",
    "get_summarization_dependencies",
    "get_summarization_repository",
    "get_summarization_service",
]
