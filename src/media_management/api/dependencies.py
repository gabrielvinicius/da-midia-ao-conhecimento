"""Dependencies for Media Management API."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.shared.infrastructure.database.db import get_db
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory, get_storage_service_factory


def get_event_bus(request: Request) -> SupportsEventBus:
    """Retrieve the shared event bus from app state."""
    if not hasattr(request.app.state, "event_bus"):
        raise RuntimeError("Event bus not initialized in app state")
    return request.app.state.event_bus


def get_media_repository(
    session: AsyncSession = Depends(get_db),
) -> MediaRepository:
    return MediaRepository(db=session)


def get_media_upload_validator() -> MediaUploadValidator:
    return MediaUploadValidator(settings=media_settings)


def get_media_read_service(
    media_repository: MediaRepository = Depends(get_media_repository),
) -> MediaReadService:
    return MediaReadService(media_repository=media_repository)


def get_media_service(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
    upload_validator: MediaUploadValidator = Depends(get_media_upload_validator),
    media_read_service: MediaReadService = Depends(get_media_read_service),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> MediaService:
    return MediaService(
        media_repository=media_repository,
        storage_service_factory=storage_factory,
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=upload_validator,
        media_read_service=media_read_service,
        event_bus=event_bus,
        emit_legacy_task=False,
    )

def get_media_queries(
    media_service: Annotated[MediaService, Depends(get_media_service)]
) -> MediaReadService:
    """Return MediaQueries (read service or proxied MediaService)."""
    return media_service

# Alias for backward compatibility if anyone imports MediaQueries from here
MediaQueries = MediaReadService
