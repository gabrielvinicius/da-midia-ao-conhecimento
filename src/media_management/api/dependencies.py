"""Dependencies for Media Management API."""

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
from src.media_management.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultUploadMetadataMapper,
    StorageServiceFactoryUploader,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.media_management.infrastructure.dependencies.data_erasers import (
    build_media_data_erasers,
)
from src.shared.infrastructure.database.db import get_db
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory, get_storage_service_factory
from src.storage.application.services.maintenance_service import (
    StorageMaintenanceService,
)
from src.storage.infrastructure.adapters.storage_maintenance_adapter import (
    StorageMaintenanceAdapter,
)


def get_event_bus(request: Request) -> SupportsEventBus:
    """Retrieve the shared event bus from app state."""
    if not hasattr(request.app.state, "event_bus"):
        raise RuntimeError(
            "Event bus não inicializado no app.state. "
            "Verifique o bootstrap (main.lifespan) para injetar a instância."
        )
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
    return MediaReadService(media_repository=MediaRepositoryAdapter(media_repository))


def get_media_service(
    media_repository: MediaRepository = Depends(get_media_repository),
    storage_factory: StorageServiceFactory = Depends(get_storage_service_factory),
    upload_validator: MediaUploadValidator = Depends(get_media_upload_validator),
    media_read_service: MediaReadService = Depends(get_media_read_service),
    event_bus: SupportsEventBus = Depends(get_event_bus),
) -> MediaService:
    return MediaService(
        media_repository=MediaRepositoryAdapter(media_repository),
        storage_uploader=StorageServiceFactoryUploader(storage_factory),
        metadata_mapper=DefaultUploadMetadataMapper(),
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=upload_validator,
        media_read_service=media_read_service,
        event_bus=event_bus,
        storage_maintenance=StorageMaintenanceService(
            storage_port=StorageMaintenanceAdapter(storage_factory),
        ),
        data_erasers=build_media_data_erasers(media_repository.db),
    )
