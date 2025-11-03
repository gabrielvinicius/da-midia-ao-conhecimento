# src/summarization/bootstrap.py
"""Dependency wiring for the simplified summarisation stack."""

from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.summarization.application.summarization_service import SummarizationService
from src.text_analysis.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.text_analysis.summarization.infrastructure.summarizer import TextRankSummarizer
from src.text_analysis.application.services import TextAnalysisService


class SummarizationContainer(containers.DeclarativeContainer):
    """Container exposing the minimal components required by the API."""

    db: providers.Provider[AsyncSession] = providers.Dependency()
    text_analysis_service: providers.Dependency[TextAnalysisService] = providers.Dependency()

    summarization_repository = providers.Factory(SummarizationRepository, db=db)
    summarizer = providers.Singleton(TextRankSummarizer)
    summarization_service = providers.Factory(
        SummarizationService,
        summarization_repo=summarization_repository,
        summarizer=summarizer,
        text_analysis_service=text_analysis_service,
    )


@dataclass(slots=True)
class SummarizationModule:
    """Public API surface for summarisation operations."""

    service: SummarizationService
    repository: SummarizationRepository


def create_summarization_container(session: AsyncSession) -> SummarizationContainer:
    """Create a container bound to the provided database session."""

    return SummarizationContainer(db=session)


async def build_summarization_module(
    container: SummarizationContainer,
) -> SummarizationModule:
    """Resolve concrete components from the dependency container."""

    return SummarizationModule(
        service=container.summarization_service(),
        repository=container.summarization_repository(),
    )


__all__ = [
    "SummarizationContainer",
    "SummarizationModule",
    "create_summarization_container",
    "build_summarization_module",
]
