from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_management.application.facade import MediaManagementFacade
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)


class MediaDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaDependencies:
    queries: MediaQueries
    upload_service: MediaUploadService
    lifecycle_service: MediaLifecycleService
    query_service: MediaQueryService
    facade: MediaManagementFacade


def get_media_dependencies() -> MediaDependencies:
    raise MediaDependenciesNotConfigured(
        "Media dependencies are not configured. Register providers in the lifespan handler."
    )


MediaDeps = Annotated[MediaDependencies, Depends(get_media_dependencies)]


def get_media_upload_service(deps: MediaDeps) -> MediaUploadService:
    return deps.upload_service


def get_media_lifecycle_service(deps: MediaDeps) -> MediaLifecycleService:
    return deps.lifecycle_service


def get_media_query_service(deps: MediaDeps) -> MediaQueryService:
    return deps.query_service


def get_media_queries(deps: MediaDeps) -> MediaQueries:
    return deps.queries


def get_media_facade(deps: MediaDeps) -> MediaManagementFacade:
    return deps.facade


__all__ = [
    "MediaDependencies",
    "MediaDependenciesNotConfigured",
    "get_media_dependencies",
    "get_media_lifecycle_service",
    "get_media_queries",
    "get_media_query_service",
    "get_media_facade",
    "get_media_upload_service",
]
