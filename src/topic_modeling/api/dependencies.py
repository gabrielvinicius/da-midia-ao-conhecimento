from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.topic_modeling.application.topic_modeling_service import TopicModelingService
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository


class TopicModelingDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TopicModelingDependencies:
    service: TopicModelingService
    repository: TopicModelingRepository


def get_topic_modeling_dependencies() -> TopicModelingDependencies:
    raise TopicModelingDependenciesNotConfigured(
        "Topic modeling dependencies are not configured. Register providers in the lifespan handler."
    )


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
    "get_topic_modeling_dependencies",
    "get_topic_modeling_repository",
    "get_topic_modeling_service",
]
