"""Dependency-injector container for the topic modeling module."""
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.topic_modeling.application.commands.handlers import (
    AnalyzeTopicsCommandHandler,
)
from src.topic_modeling.application.topic_modeling_service import TopicModelingService
from src.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
from src.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics
from src.topic_modeling.infrastructure.task_scheduler import (
    CeleryTopicModelingTaskScheduler,
)
from src.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)
from src.shared.events.event_bus import EventBus
from src.topic_modeling.application.event_handlers import (
    register_event_handlers as register_topic_handlers,
)


class TopicModelingContainer(containers.DeclarativeContainer):
    """IoC container that wires topic modeling dependencies."""

    db: providers.Provider[AsyncSession] = providers.Dependency()
    event_bus = providers.Dependency(default=None)
    media_queries = providers.Dependency(default=None)
    transcription_queries = providers.Dependency(default=None)

    topic_modeling_repository = providers.Factory(
        TopicModelingRepository,
        db=db,
    )
    topic_modeling_task_scheduler = providers.Factory(
        CeleryTopicModelingTaskScheduler,
    )
    topic_modeling_logger = providers.Singleton(StructuredTopicModelingLogger)
    topic_modeling_metrics = providers.Singleton(PrometheusTopicModelingMetrics)
    topic_modeler = providers.Singleton(BERTopicModeler)

    topic_modeling_service = providers.Factory(
        TopicModelingService,
        topic_modeler=topic_modeler,
        topic_modeling_repo=topic_modeling_repository,
        task_scheduler=topic_modeling_task_scheduler,
        topic_logger=topic_modeling_logger,
        topic_metrics=topic_modeling_metrics,
    )

    analyze_topics_command_handler = providers.Factory(
        AnalyzeTopicsCommandHandler,
        topic_modeling_service=topic_modeling_service,
        task_scheduler=topic_modeling_task_scheduler,
    )


@dataclass
class TopicModelingModule:
    service: TopicModelingService
    repository: TopicModelingRepository


async def build_topic_modeling_module(
    session: AsyncSession,
    event_bus: EventBus,
    media_queries,
    transcription_queries,
) -> TopicModelingModule:
    container = TopicModelingContainer(
        db=session,
        event_bus=event_bus,
        media_queries=providers.Object(media_queries),
        transcription_queries=providers.Object(transcription_queries),
    )

    module = TopicModelingModule(
        service=container.topic_modeling_service(),
        repository=container.topic_modeling_repository(),
    )
    await register_topic_handlers(event_bus)
    return module


__all__ = ["TopicModelingContainer", "TopicModelingModule", "build_topic_modeling_module"]
