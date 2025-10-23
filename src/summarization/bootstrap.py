# src/summarization/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.task_scheduler import CelerySummarizationTaskScheduler
from src.summarization.infrastructure.logging import StructuredSummaryLogger
from src.summarization.infrastructure.metrics import PrometheusSummaryMetrics

# Consolidated Service
from src.summarization.application.summarization_service import SummarizationService

class SummarizationContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Infrastructure Services
    summarization_repository = providers.Factory(SummarizationRepository, db=db)
    summarization_task_scheduler = providers.Factory(CelerySummarizationTaskScheduler)
    summary_logger = providers.Singleton(StructuredSummaryLogger)
    summary_metrics = providers.Singleton(PrometheusSummaryMetrics)

    # Consolidated Application Service
    summarization_service = providers.Factory(
        SummarizationService,
        summarization_repo=summarization_repository,
        task_scheduler=summarization_task_scheduler,
        summary_logger=summary_logger,
        summary_metrics=summary_metrics
    )
