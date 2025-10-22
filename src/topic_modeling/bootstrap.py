# src/topic_modeling/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.topic_modeling.domain.interfaces import (
    ITopicModeler,
    ITopicModelingRepository,
    ITopicModelingTaskScheduler,
    TopicModelingOperationLogger,
    TopicModelingMetrics
)
from src.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.topic_modeling.infrastructure.task_scheduler import CeleryTopicModelingTaskScheduler
from src.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
from src.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics
from src.topic_modeling.application.commands.handlers import AnalyzeTopicsCommandHandler
from src.topic_modeling.application.topic_modeling_service import TopicModelingService

class TopicModelingContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Implementações concretas das interfaces de domínio
    topic_modeler: providers.Provider[ITopicModeler] = providers.Factory(
        BERTopicModeler
    )
    topic_modeling_repository: providers.Provider[ITopicModelingRepository] = providers.Factory(
        TopicModelingRepository,
        db=db
    )
    topic_modeling_task_scheduler: providers.Provider[ITopicModelingTaskScheduler] = providers.Factory(
        CeleryTopicModelingTaskScheduler
    )
    topic_logger: providers.Provider[TopicModelingOperationLogger] = providers.Singleton(
        StructuredTopicModelingLogger
    )
    topic_metrics: providers.Provider[TopicModelingMetrics] = providers.Singleton(
        PrometheusTopicModelingMetrics
    )

    # Command Handlers
    analyze_topics_command_handler: providers.Provider[AnalyzeTopicsCommandHandler] = providers.Factory(
        AnalyzeTopicsCommandHandler,
        topic_modeler=topic_modeler,
        topic_modeling_repo=topic_modeling_repository,
        topic_logger=topic_logger,
        topic_metrics=topic_metrics
    )

    # Serviços de Aplicação
    topic_modeling_service: providers.Provider[TopicModelingService] = providers.Factory(
        TopicModelingService,
        topic_modeler=topic_modeler,
        topic_modeling_repo=topic_modeling_repository,
        task_scheduler=topic_modeling_task_scheduler,
        topic_logger=topic_logger,
        topic_metrics=topic_metrics
    )
