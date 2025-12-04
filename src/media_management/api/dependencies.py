"""Dependencies for Media Management API."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.commands.use_cases import (
    CleanupOrphanedFiles,
    CreateMedia,
    DeleteMedia,
    ReprocessMedia,
)
from src.media_management.application.commands.validators import MediaUploadValidator
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.use_cases import (
    GetMedia,
    GetMediaStatistics,
    ListMedia,
)
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


def get_media_access_policy() -> MediaAccessPolicy:
    return MediaAccessPolicy()


def get_media_upload_validator() -> MediaUploadValidator:
    return MediaUploadValidator(settings=settings)


def get_create_media(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
    upload_validator: MediaUploadValidator = Depends(get_media_upload_validator),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> CreateMedia:
    return CreateMedia.with_default_components(
        media_repository=media_repository,
        storage_service_factory=storage_factory,
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=upload_validator,
        event_bus=event_bus,
        # Default to True as per standard behavior, unless overridden
        emit_legacy_task=True,
    )


def get_delete_media(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
    access_policy: MediaAccessPolicy = Depends(get_media_access_policy),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> DeleteMedia:
    return DeleteMedia(
        media_repository=media_repository,
        storage_factory=storage_factory,
        access_policy=access_policy,
        event_bus=event_bus,
        metrics=PrometheusMediaMetrics(),
    )


def get_reprocess_media(
    media_repository: MediaRepository = Depends(get_media_repository),
    access_policy: MediaAccessPolicy = Depends(get_media_access_policy),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> ReprocessMedia:
    return ReprocessMedia(
        media_repository=media_repository,
        access_policy=access_policy,
        event_bus=event_bus,
        metrics=PrometheusMediaMetrics(),
    )


def get_cleanup_media(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
) -> CleanupOrphanedFiles:
    return CleanupOrphanedFiles(
        media_repository=media_repository,
        storage_factory=storage_factory,
    )


def get_get_media(
    media_repository: MediaRepository = Depends(get_media_repository),
) -> GetMedia:
    return GetMedia(repository=media_repository)


def get_list_media(
    media_repository: MediaRepository = Depends(get_media_repository),
) -> ListMedia:
    return ListMedia(repository=media_repository)


def get_get_media_statistics(
    media_repository: MediaRepository = Depends(get_media_repository),
) -> GetMediaStatistics:
    return GetMediaStatistics(repository=media_repository)
