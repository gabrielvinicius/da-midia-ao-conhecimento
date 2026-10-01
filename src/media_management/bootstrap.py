# src/media_management/bootstrap.py
"""Bootstrap media management module."""
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.repositories.processing_stats_repository import (
    ProcessingStatsRepository,
)
from src.media_management.api.dependencies import (
    get_media_service,
)
from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultStorageUploader,
    DefaultUploadMetadataMapper,
    StorageUploaderAdapter,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.media_processing.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.ports import TranscriptionQueryPort
from src.media_management.infrastructure.adapters.storage_downloader_adapter import (
    StorageDownloaderAdapter,
)
from src.media_management.infrastructure.adapters.file_validator_adapter import (
    MediaFileReferenceValidator,
)
from src.shared.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from src.media_management.infrastructure.dependencies.data_erasers import (
    build_media_data_erasers,
)
from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
    TranscriptionQueryAdapter,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_speech_recognizer,
)
from src.media_processing.infrastructure.logging import structured_transcription_logger
from src.media_processing.infrastructure.metrics import (
    prometheus_transcription_metrics,
)
from src.media_processing.infrastructure.repositories import transcription_repository
from src.media_processing.infrastructure.adapters.celery_task_schedulers import (
    CeleryTranscriptionTaskScheduler,
)

StructuredTranscriptionLogger = (
    structured_transcription_logger.StructuredTranscriptionLogger
)
PrometheusTranscriptionMetrics = (
    prometheus_transcription_metrics.PrometheusTranscriptionMetrics
)
TranscriptionRepository = transcription_repository.TranscriptionRepository
from src.shared.domain.events import (
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.application.event_bus import SupportsEventBus
from src.storage.application.services.maintenance_service import (
    StorageMaintenanceService,
)
from src.storage.infrastructure.adapters.storage_maintenance_adapter import (
    StorageMaintenanceAdapter,
)


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    media_service: MediaService

    transcription_service: TranscriptionService
    # Read-side: consulta de transcrições (para outros contextos, ex.: text_analysis).
    transcription_queries: TranscriptionQueryPort


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""

    media_service: MediaService

    # For backward compatibility if accessing properties directly
    @property
    def queries(self):
        return self.media_service


def build_media_components(
    session: AsyncSession,
    *,
    storage_service_factory: Any,
    metrics_service: Any,
    event_bus: Optional[SupportsEventBus] = None,
    storage_provider: str = "local",
    subscribe: bool = True,
) -> Tuple[MediaModule, MediaAdminContext]:
    """Compose the media module without relying on dependency-injector."""
    media_repository = MediaRepository(db=session)
    media_repo_adapter = MediaRepositoryAdapter(media_repository)
    media_read_service = MediaReadService(media_repository=media_repo_adapter)
    media_upload_validator = MediaUploadValidator(settings=media_settings)

    # Processing dependencies
    transcription_repository = TranscriptionRepository(db=session)
    transcription_queries = TranscriptionQueryAdapter(transcription_repository)
    transcription_metrics = PrometheusTranscriptionMetrics()
    transcription_storage_service = storage_service_factory.create_storage_service(
        storage_provider
    )

    storage_maintenance_service = StorageMaintenanceService(
        storage_port=StorageMaintenanceAdapter(storage_service_factory)
    )
    # Register validators
    storage_maintenance_service.register_validator(
        MediaFileReferenceValidator(media_repository)
    )

    media_service = MediaService(
        media_repository=media_repo_adapter,
        storage_uploader=DefaultStorageUploader(StorageUploaderAdapter(storage_service_factory)),
        metadata_mapper=DefaultUploadMetadataMapper(),
        metrics_service=metrics_service,
        upload_validator=media_upload_validator,
        media_read_service=media_read_service,
        event_bus=event_bus,
        storage_maintenance=storage_maintenance_service,
        data_erasers=build_media_data_erasers(session),
        unit_of_work=SqlAlchemyUnitOfWork(session),
        storage_downloader=StorageDownloaderAdapter(storage_service_factory),
    )
    transcription_service = TranscriptionService(
        transcription_repo=transcription_repository,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=transcription_metrics,
        storage_service=transcription_storage_service,
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        event_bus=event_bus,
        stats_recorder=ProcessingStatsRepository(session),  # estimativas
    )

    media_event_handlers = MediaEventHandlers(media_service, event_bus=event_bus)

    if event_bus and subscribe:
        # TextContentReady handled in text_analysis module
        event_bus.subscribe(
            TranscriptionCompleted,
            media_event_handlers.handle_transcription_completed,
        )
        event_bus.subscribe(
            TranscriptionFailed,
            media_event_handlers.handle_transcription_failed,
        )

    module = MediaModule(
        media_service=media_service,
        transcription_service=transcription_service,
        transcription_queries=transcription_queries,
    )

    admin_context = MediaAdminContext(
        media_service=media_service,
    )

    return module, admin_context


def bind_media_module(app: FastAPI, module: MediaModule) -> None:
    """Register dependency overrides for media use cases."""
    from fastapi import Depends, Request
    from src.shared.infrastructure.database.db import get_db
    from src.storage.infrastructure.dependencies import StorageServiceFactory

    # Factory can be instantiated once or per request (it's lightweight)
    storage_factory = StorageServiceFactory()

    async def resolve_media_service(request: Request, session: AsyncSession = Depends(get_db)):
        # Retrieve event bus from app state (Instance A)
        event_bus = getattr(request.app.state, "event_bus", None)
        
        # Re-build the module logic using the current request's session
        m, _ = build_media_components(
            session=session,
            storage_service_factory=storage_factory,
            metrics_service=None, # Optional for per-request instances
            event_bus=event_bus,
            subscribe=False # Do not subscribe handlers per-request!
        )
        return m.media_service

    app.dependency_overrides[get_media_service] = resolve_media_service

    async def resolve_transcription_deps(request: Request, session: AsyncSession = Depends(get_db)):
        event_bus = getattr(request.app.state, "event_bus", None)
        m, _ = build_media_components(
            session=session,
            storage_service_factory=storage_factory,
            metrics_service=None,
            event_bus=event_bus,
            subscribe=False
        )
        return TranscriptionDependencies(service=m.transcription_service)

    app.dependency_overrides[get_transcription_dependencies] = resolve_transcription_deps


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "bind_media_module",
    "build_media_components",
]
