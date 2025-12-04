"""Dependencies for Media Management API."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.services.media_service import MediaService
from src.media_management.application.commands.validators import MediaUploadValidator
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.shared.config.settings import settings
from src.shared.events.bus import SupportsEventBus
from src.shared.infrastructure.database import get_db
from src.storage.infrastructure.dependencies import (
    StorageServiceFactory,
    get_storage_service_factory,
)


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
    return MediaUploadValidator(settings=settings)


def get_media_service(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
    upload_validator: MediaUploadValidator = Depends(get_media_upload_validator),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> MediaService:
    return MediaService(
        media_repository=media_repository,
        storage_service_factory=storage_factory,
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=upload_validator,
        event_bus=event_bus,
        emit_legacy_task=True,
    )