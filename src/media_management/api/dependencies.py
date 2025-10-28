# src/media_management/api/dependencies.py
from typing import Annotated
from fastapi import Depends, Request

from src.media_management.application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)


def get_container(request: Request) -> dict:
    return request.app.state.container


def get_media_upload_service(
    container: Annotated[dict, Depends(get_container)]
) -> MediaUploadService:
    return container["media_upload_service"]


def get_media_lifecycle_service(
    container: Annotated[dict, Depends(get_container)]
) -> MediaLifecycleService:
    return container["media_lifecycle_service"]


def get_media_query_service(
    container: Annotated[dict, Depends(get_container)]
) -> MediaQueryService:
    return container["media_query_service"]
