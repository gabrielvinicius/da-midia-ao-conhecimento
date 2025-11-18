"""Dependency-injector configuration for the topic modeling module."""

from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.text_analysis.topic_modeling.application.commands.handlers import (
    AnalyzeTopicsCommandHandler,
)
from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.shared.config.settings import settings
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import (
    create_registry,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)


class TopicModelingContainer(containers.DeclarativeContainer):
    """IoC container wiring topic modeling dependencies."""

    db: providers.Provider[AsyncSession] = providers.Dependency()
    text_analysis_service = providers.Dependency(default=None)
    topic_modeler_registry = providers.Dependency()

    topic_modeling_repository = providers.Factory(
        TopicModelingRepository,
        db=db,
    )
    topic_modeling_logger = providers.Singleton(StructuredTopicModelingLogger)
    topic_modeling_metrics = providers.Singleton(PrometheusTopicModelingMetrics)
    topic_modeling_service = providers.Factory(
        TopicModelingService,
        topic_modeler_registry=topic_modeler_registry,
        topic_modeling_repo=topic_modeling_repository,
        text_analysis_service=text_analysis_service,
        topic_logger=topic_modeling_logger,
        topic_metrics=topic_modeling_metrics,
    )

    analyze_topics_command_handler = providers.Factory(
        AnalyzeTopicsCommandHandler,
        topic_modeling_service=topic_modeling_service,
    )


@dataclass
class TopicModelingModule:
    service: TopicModelingService
    repository: TopicModelingRepository


async def build_topic_modeling_module(
    session: AsyncSession,
    *,
    text_analysis_service,
) -> TopicModelingModule:
    registry = create_registry(
        enabled=settings.topic_modeling_enabled_list,
        default_provider=settings.TOPIC_MODELING_DEFAULT_PROVIDER,
        plugin_modules=settings.topic_modeling_plugin_modules,
        overrides=settings.topic_modeling_provider_overrides,
    )
    container = TopicModelingContainer(
        db=session,
        text_analysis_service=providers.Object(text_analysis_service),
        topic_modeler_registry=providers.Object(registry),
    )

    module = TopicModelingModule(
        service=container.topic_modeling_service(),
        repository=container.topic_modeling_repository(),
    )
    return module


__all__ = ["TopicModelingContainer", "TopicModelingModule", "build_topic_modeling_module"]
