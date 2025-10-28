# src/summarization/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

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

