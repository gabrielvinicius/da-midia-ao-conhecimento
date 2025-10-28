# src/summarization/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.events.event_bus import EventBus

# Concrete Implementations
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.task_scheduler import CelerySummarizationTaskScheduler
from src.summarization.infrastructure.logging import StructuredSummaryLogger
from src.summarization.infrastructure.metrics import PrometheusSummaryMetrics
from src.summarization.infrastructure.summarizer import TextRankSummarizer

from src.summarization.application.commands.handlers import (
    ProcessSummaryCommandHandler,
    RequestSummaryCommandHandler,
)

# Consolidated Service
from src.summarization.application.summarization_service import SummarizationService
from src.summarization.application.event_handlers import (
    register_event_handlers as register_summary_handlers,
)


class SummarizationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    event_bus = providers.Dependency(default=None)
    transcription_queries = providers.Dependency(default=None)
    media_queries = providers.Dependency(default=None)
    connection_manager = providers.Dependency(default=None)

    # Infrastructure Services
    summarization_repository = providers.Factory(SummarizationRepository, db=db)
    summarization_task_scheduler = providers.Factory(CelerySummarizationTaskScheduler)
    summary_logger = providers.Singleton(StructuredSummaryLogger)
    summary_metrics = providers.Singleton(PrometheusSummaryMetrics)
    summarizer = providers.Singleton(TextRankSummarizer)

    request_summary_command_handler = providers.Factory(
        RequestSummaryCommandHandler,
        event_bus=event_bus,
        task_scheduler=summarization_task_scheduler,
    )

    process_summary_command_handler = providers.Factory(
        ProcessSummaryCommandHandler,
        summarizer=summarizer,
        summary_repo=summarization_repository,
        transcription_queries=transcription_queries,
        metrics_service=summary_metrics,
        event_bus=event_bus,
        connection_manager=connection_manager,
    )

    # Consolidated Application Service
    summarization_service = providers.Factory(
        SummarizationService,
        summarization_repo=summarization_repository,
        task_scheduler=summarization_task_scheduler,
        summary_logger=summary_logger,
        summary_metrics=summary_metrics
    )


@dataclass
class SummarizationModule:
    """Public API surface for summarization operations."""

    service: SummarizationService
    request_handler: RequestSummaryCommandHandler
    process_handler: ProcessSummaryCommandHandler


def create_summarization_container(
    session: AsyncSession,
    *,
    event_bus,
    transcription_queries,
    media_queries,
    connection_manager,
) -> SummarizationContainer:
    return SummarizationContainer(
        db=session,
        event_bus=event_bus,
        transcription_queries=transcription_queries,
        media_queries=media_queries,
        connection_manager=connection_manager,
    )


async def build_summarization_module(
    container: SummarizationContainer,
    *,
    event_bus: EventBus,
    media_queries: MediaQueries,
) -> SummarizationModule:
    module = SummarizationModule(
        service=container.summarization_service(),
        request_handler=container.request_summary_command_handler(),
        process_handler=container.process_summary_command_handler(),
    )
    repository = container.summarization_repository()
    task_scheduler = container.summarization_task_scheduler()
    await register_summary_handlers(
        event_bus,
        repository,
        media_queries,
        task_scheduler,
    )
    return module


__all__ = [
    "SummarizationContainer",
    "SummarizationModule",
    "create_summarization_container",
    "build_summarization_module",
]
