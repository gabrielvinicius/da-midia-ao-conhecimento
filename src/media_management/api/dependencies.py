from typing import Annotated
from fastapi import Depends, Request

from src.media_management.application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_media_upload_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> MediaUploadService:
    return modules.media_management.upload_service


def get_media_lifecycle_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> MediaLifecycleService:
    return modules.media_management.lifecycle_service


def get_media_query_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> MediaQueryService:
    return modules.media_management.query_service
