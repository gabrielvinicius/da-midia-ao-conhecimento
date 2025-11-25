from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_management.application.facade import MediaOrchestrator
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import MediaService


class MediaDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaDependencies:
    queries: MediaQueries
    service: MediaService
    orchestrator: MediaOrchestrator


def get_media_dependencies() -> MediaDependencies:
    raise MediaDependenciesNotConfigured(
        "Media dependencies are not configured. Register providers in the lifespan handler."
    )


MediaDeps = Annotated[MediaDependencies, Depends(get_media_dependencies)]


def get_media_service(deps: MediaDeps) -> MediaService:
    return deps.service


def get_media_queries(deps: MediaDeps) -> MediaQueries:
    return deps.queries


def get_media_orchestrator(deps: MediaDeps) -> MediaOrchestrator:
    return deps.orchestrator


__all__ = [
    "MediaDependencies",
    "MediaDependenciesNotConfigured",
    "get_media_dependencies",
    "get_media_queries",
    "get_media_service",
    "get_media_orchestrator",
]
