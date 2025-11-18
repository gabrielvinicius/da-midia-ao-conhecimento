from fastapi import Depends

from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)


class TopicModelingDependenciesNotConfigured(RuntimeError):
    pass


_topic_service: TopicModelingService | None = None
_topic_repository: TopicModelingRepository | None = None


def configure_topic_modeling_dependencies(
    *,
    service: TopicModelingService,
    repository: TopicModelingRepository,
) -> None:
    global _topic_service, _topic_repository
    _topic_service = service
    _topic_repository = repository


def get_topic_modeling_service() -> TopicModelingService:
    if _topic_service is None:
        raise TopicModelingDependenciesNotConfigured(
            "Topic modeling service not configured. Register it during app startup."
        )
    return _topic_service


def get_topic_modeling_repository() -> TopicModelingRepository:
    if _topic_repository is None:
        raise TopicModelingDependenciesNotConfigured(
            "Topic modeling repository not configured. Register it during app startup."
        )
    return _topic_repository


__all__ = [
    "TopicModelingDependenciesNotConfigured",
    "configure_topic_modeling_dependencies",
    "get_topic_modeling_repository",
    "get_topic_modeling_service",
]
