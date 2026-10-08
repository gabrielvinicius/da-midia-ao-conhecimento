"""Montagem dos serviços de mídias: um único lugar para a API e os workers.

Antes, o MediaService era montado em três lugares, e as montagens divergiam:
a da API gravava sempre no armazenamento local, ignorando o escolhido no
envio, e só ela tinha o leitor de arquivos usado na reprodução.
"""
from __future__ import annotations

from typing import Optional

from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.application.services.media_read_service import MediaReadService
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.media_management.infrastructure.adapters.storage_downloader_adapter import (
    StorageDownloaderAdapter,
)
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultUploadMetadataMapper,
    StorageServiceFactoryUploader,
)
from src.media_management.infrastructure.adapters.direct_link_fetcher_adapter import DirectLinkFetcherAdapter
from src.media_management.infrastructure.adapters.youtube_fetcher_adapter import YoutubeFetcherAdapter
from src.media_management.infrastructure.dependencies.data_erasers import (
    build_media_data_erasers,
)
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.shared.application.event_bus import SupportsEventBus
from src.shared.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.storage.application.services.maintenance_service import (
    StorageMaintenanceService,
)
from src.storage.infrastructure.adapters.storage_maintenance_adapter import (
    StorageMaintenanceAdapter,
)
from src.storage.infrastructure.dependencies import StorageServiceFactory


def build_media_read_service(session) -> MediaReadService:
    return MediaReadService(media_repository=MediaRepositoryAdapter(MediaRepository(db=session)))


def build_media_service(
    *,
    session,
    storage_factory: StorageServiceFactory,
    event_bus: Optional[SupportsEventBus],
) -> MediaService:
    """Casos de uso das mídias (envio, exclusão, reprocessamento, ciclo de vida)."""
    media_repository = MediaRepository(db=session)
    storage_maintenance = StorageMaintenanceService(
        storage_port=StorageMaintenanceAdapter(storage_factory)
    )
    return MediaService(
        media_repository=MediaRepositoryAdapter(media_repository),
        storage_uploader=StorageServiceFactoryUploader(storage_factory),
        metadata_mapper=DefaultUploadMetadataMapper(),
        metrics_service=PrometheusMediaMetrics(),
        upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=build_media_read_service(session),
        event_bus=event_bus,
        storage_maintenance=storage_maintenance,
        data_erasers=build_media_data_erasers(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        storage_downloader=StorageDownloaderAdapter(storage_factory),
        url_fetcher=YoutubeFetcherAdapter(
            max_bytes=media_settings.media_max_file_size_bytes,
            max_seconds=media_settings.media_url_import_max_minutes * 60,
        ),
        direct_link_fetcher=DirectLinkFetcherAdapter(
            max_bytes=media_settings.media_max_file_size_bytes,
            allowed_extensions=[
                *media_settings.media_allowed_video_extensions,
                *media_settings.media_allowed_audio_extensions,
                *media_settings.media_allowed_text_extensions,
            ],
        ),
        url_import_enabled=media_settings.media_url_import_enabled,
    )


def build_media_event_handlers(
    *,
    session,
    storage_factory: StorageServiceFactory,
    event_bus: SupportsEventBus,
) -> MediaEventHandlers:
    """Reações do módulo de mídias aos eventos do processamento."""
    service = build_media_service(session=session, storage_factory=storage_factory, event_bus=event_bus)
    return MediaEventHandlers(service, event_bus=event_bus)


__all__ = ["build_media_event_handlers", "build_media_read_service", "build_media_service"]
