from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.summarization.application.summarization_service import SummarizationService


class SummarizationDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class SummarizationDependencies:
    service: SummarizationService


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


__all__ = [
    "SummarizationDependencies",
    "SummarizationDependenciesNotConfigured",
    "get_summarization_dependencies",
    "get_summarization_service",
]
