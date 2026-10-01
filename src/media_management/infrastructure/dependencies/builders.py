from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.application.services.media_read_service import MediaReadService
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultUploadMetadataMapper,
    StorageServiceFactoryUploader,
)
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.media_management.infrastructure.dependencies.data_erasers import (
    build_media_data_erasers,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.application.services.maintenance_service import (
    StorageMaintenanceService,
)
from src.storage.infrastructure.adapters.storage_maintenance_adapter import (
    StorageMaintenanceAdapter,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory


def build_media_service(
    *,
    session: AsyncSession,
    storage_factory: StorageServiceFactory,
    event_bus: SupportsEventBus,
) -> MediaService:
    """Constrói o MediaService (command-side) para uso em APIs e handlers."""

    media_repo = MediaRepository(db=session)
    media_repo_adapter = MediaRepositoryAdapter(media_repo)

    media_read_service = MediaReadService(media_repository=media_repo_adapter)
    upload_validator = MediaUploadValidator(settings=media_settings)

    return MediaService(
        media_repository=media_repo_adapter,
        storage_uploader=StorageServiceFactoryUploader(storage_factory),
        metadata_mapper=DefaultUploadMetadataMapper(),
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=upload_validator,
        media_read_service=media_read_service,
        event_bus=event_bus,
        storage_maintenance=StorageMaintenanceService(
            storage_port=StorageMaintenanceAdapter(storage_factory),
        ),
        data_erasers=build_media_data_erasers(session),
    )


def build_media_event_handlers(
    *,
    session: AsyncSession,
    storage_factory: StorageServiceFactory,
    event_bus: SupportsEventBus,
) -> MediaEventHandlers:
    """Constrói handlers do media_management com dependências por evento."""

    service = build_media_service(
        session=session,
        storage_factory=storage_factory,
        event_bus=event_bus,
    )
    return MediaEventHandlers(service)


__all__ = ["build_media_service", "build_media_event_handlers"]
