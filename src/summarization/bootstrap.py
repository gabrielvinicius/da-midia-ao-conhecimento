# src/summarization/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.summarization.domain.interfaces import (
    ISummarizer,
    ISummarizationRepository,
    ISummarizationTaskScheduler,
    SummaryOperationLogger,
    SummaryMetrics
)
from src.summarization.infrastructure.summarizer import TextRankSummarizer
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.task_scheduler import CelerySummarizationTaskScheduler
from src.summarization.infrastructure.logging import StructuredSummaryLogger
from src.summarization.infrastructure.metrics import PrometheusSummaryMetrics
from src.summarization.application.commands.handlers import ProcessSummaryCommandHandler, RequestSummaryCommandHandler
from src.summarization.application.summarization_service import SummarizationService

class SummarizationContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Implementações concretas das interfaces de domínio
    summarizer: providers.Provider[ISummarizer] = providers.Factory(
        TextRankSummarizer
    )
    summarization_repository: providers.Provider[ISummarizationRepository] = providers.Factory(
        SummarizationRepository,
        db=db
    )
    summarization_task_scheduler: providers.Provider[ISummarizationTaskScheduler] = providers.Factory(
        CelerySummarizationTaskScheduler
    )
    summary_logger: providers.Provider[SummaryOperationLogger] = providers.Singleton(
        StructuredSummaryLogger
    )
    summary_metrics: providers.Provider[SummaryMetrics] = providers.Singleton(
        PrometheusSummaryMetrics
    )

    # Serviços de Aplicação
    summarization_service: providers.Provider[SummarizationService] = providers.Factory(
        SummarizationService,
        summarizer=summarizer,
        summarization_repo=summarization_repository,
        task_scheduler=summarization_task_scheduler,
        summary_logger=summary_logger,
        summary_metrics=summary_metrics
    )

    # Command Handlers
    process_summary_command_handler: providers.Provider[ProcessSummaryCommandHandler] = providers.Factory(
        ProcessSummaryCommandHandler,
        summarization_repo=summarization_repository,
        summary_logger=summary_logger,
        summary_metrics=summary_metrics
    )
    request_summary_command_handler: providers.Provider[RequestSummaryCommandHandler] = providers.Factory(
        RequestSummaryCommandHandler,
        summarization_repo=summarization_repository,
        summarization_task_scheduler=summarization_task_scheduler,
        summary_logger=summary_logger,
        summary_metrics=summary_metrics
    )