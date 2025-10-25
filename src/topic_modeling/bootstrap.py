# src/topic_modeling/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.topic_modeling.infrastructure.task_scheduler import CeleryTopicModelingTaskScheduler
from src.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
from src.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics

# Consolidated Service
from src.topic_modeling.application.topic_modeling_service import TopicModelingService

class TopicModelingContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Infrastructure Services
    topic_modeling_repository = providers.Factory(TopicModelingRepository, db=db)
    topic_modeler = providers.Factory(BERTopicModeler)
    topic_modeling_task_scheduler = providers.Factory(CeleryTopicModelingTaskScheduler)
    topic_logger = providers.Singleton(StructuredTopicModelingLogger)
    topic_metrics = providers.Singleton(PrometheusTopicModelingMetrics)

    # Consolidated Application Service
    topic_modeling_service = providers.Factory(
        TopicModelingService,
        topic_modeler=topic_modeler,
        topic_modeling_repo=topic_modeling_repository,
        task_scheduler=topic_modeling_task_scheduler,
        topic_logger=topic_logger,
        topic_metrics=topic_metrics
    )