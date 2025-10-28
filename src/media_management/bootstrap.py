# src/media_management/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)
from src.media_management.application.validators import MediaUploadValidator
from src.media_management.config.settings import MediaSettings
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)


class MediaManagementContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_service_factory = providers.Dependency()
    event_bus = providers.Dependency()
    metrics_service = providers.Dependency()

    # Config
    media_settings = providers.Singleton(MediaSettings)

    # Implementações concretas
    media_repository = providers.Factory(
        MediaRepository,
        db=db
    )
    media_queries = providers.Factory(
        MediaQueries,
        media_repository=media_repository
    )
    media_logger = providers.Singleton(
        StructuredMediaLogger
    )
    media_metrics = providers.Singleton(
        PrometheusMediaMetrics
    )

    create_media_command_handler = providers.Factory(
        CreateMediaCommandHandler,
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus,
        metrics_service=metrics_service,
    )

    # Command Handlers (Delete and Reprocess remain for now)
    delete_media_command_handler = providers.Factory(
        DeleteMediaCommandHandler,
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics
    )
    reprocess_media_command_handler = providers.Factory(
        ReprocessMediaCommandHandler,
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics
    )

    media_access_policy = providers.Factory(MediaAccessPolicy)

    media_upload_validator = providers.Factory(
        MediaUploadValidator,
        settings=media_settings,
    )

    media_upload_service = providers.Factory(
        MediaUploadService,
        create_media_handler=create_media_command_handler,
        upload_validator=media_upload_validator,
    )

    media_lifecycle_service = providers.Factory(
        MediaLifecycleService,
        media_repository=media_repository,
        delete_media_handler=delete_media_command_handler,
        reprocess_media_handler=reprocess_media_command_handler,
        access_policy=media_access_policy,
    )

    media_query_service = providers.Factory(
        MediaQueryService,
        media_queries=media_queries,
        access_policy=media_access_policy,
    )


@dataclass
class MediaManagementModule:
    queries: MediaQueries
    upload_service: MediaUploadService
    lifecycle_service: MediaLifecycleService
    query_service: MediaQueryService
    access_policy: MediaAccessPolicy
    upload_validator: MediaUploadValidator
    create_media_handler: CreateMediaCommandHandler
    delete_media_handler: DeleteMediaCommandHandler
    reprocess_media_handler: ReprocessMediaCommandHandler


def build_media_management_module(
    session: AsyncSession,
    storage_service_factory,
    event_bus,
    metrics_service,
) -> MediaManagementModule:
    container = MediaManagementContainer()
    container.db.override(session)
    container.storage_service_factory.override(storage_service_factory)
    container.event_bus.override(event_bus)
    container.metrics_service.override(metrics_service)

    return MediaManagementModule(
        queries=container.media_queries(),
        upload_service=container.media_upload_service(),
        lifecycle_service=container.media_lifecycle_service(),
        query_service=container.media_query_service(),
        access_policy=container.media_access_policy(),
        upload_validator=container.media_upload_validator(),
        create_media_handler=container.create_media_command_handler(),
        delete_media_handler=container.delete_media_command_handler(),
        reprocess_media_handler=container.reprocess_media_command_handler(),
    )
