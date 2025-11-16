from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)


class TopicModelingDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TopicModelingDependencies:
    service: TopicModelingService
    repository: TopicModelingRepository


_configured_topic_dependencies: TopicModelingDependencies | None = None


def configure_topic_modeling_dependencies(
    dependencies: TopicModelingDependencies,
) -> None:
    global _configured_topic_dependencies
    _configured_topic_dependencies = dependencies


def get_topic_modeling_dependencies() -> TopicModelingDependencies:
    if _configured_topic_dependencies is None:
        raise TopicModelingDependenciesNotConfigured(
            "Topic modeling dependencies are not configured. Register providers in the lifespan handler."
        )
    return _configured_topic_dependencies


TopicDeps = Annotated[
    TopicModelingDependencies, Depends(get_topic_modeling_dependencies)
]


def get_topic_modeling_service(
    deps: TopicDeps,
) -> TopicModelingService:
    return deps.service


def get_topic_modeling_repository(
    deps: TopicDeps,
) -> TopicModelingRepository:
    return deps.repository


__all__ = [
    "TopicModelingDependencies",
    "TopicModelingDependenciesNotConfigured",
    "configure_topic_modeling_dependencies",
    "get_topic_modeling_dependencies",
    "get_topic_modeling_repository",
    "get_topic_modeling_service",
]
