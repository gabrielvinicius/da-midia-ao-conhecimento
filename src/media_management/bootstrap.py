from dataclasses import dataclass
from typing import Any, Tuple, Optional

from src.shared.events.bus import SupportsEventBus

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.facade import MediaManagementFacade
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


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    queries: MediaQueries
    upload_service: MediaUploadService
    lifecycle_service: MediaLifecycleService
    query_service: MediaQueryService
    facade: MediaManagementFacade
    access_policy: MediaAccessPolicy


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""

    queries: MediaQueries
    delete_media_handler: DeleteMediaCommandHandler
    reprocess_media_handler: ReprocessMediaCommandHandler


def build_media_components(
    session: AsyncSession,
    *,
    storage_service_factory: Any,
    metrics_service: Any,
    event_bus: Optional[SupportsEventBus] = None,
    emit_legacy_media_task: bool = True,
) -> Tuple[MediaModule, MediaAdminContext]:
    """Compose the media module without relying on dependency-injector."""

    media_repository = MediaRepository(db=session)
    media_queries = MediaQueries(media_repository=media_repository)
    media_logger = StructuredMediaLogger()
    media_metrics = PrometheusMediaMetrics()
    media_access_policy = MediaAccessPolicy()

    create_media_handler = CreateMediaCommandHandler.with_default_components(
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        metrics_service=metrics_service,
        event_bus=event_bus,
        emit_legacy_task=emit_legacy_media_task,
    )

    delete_media_handler = DeleteMediaCommandHandler(
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics,
    )

    reprocess_media_handler = ReprocessMediaCommandHandler(
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics,
    )

    media_upload_validator = MediaUploadValidator(settings=MediaSettings())

    media_upload_service = MediaUploadService(
        create_media_handler=create_media_handler,
        upload_validator=media_upload_validator,
    )

    media_lifecycle_service = MediaLifecycleService(
        media_repository=media_repository,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
        access_policy=media_access_policy,
    )

    media_query_service = MediaQueryService(
        media_queries=media_queries,
        access_policy=media_access_policy,
    )

    facade = MediaManagementFacade(
        queries=media_queries,
        upload_service=media_upload_service,
        lifecycle_service=media_lifecycle_service,
        query_service=media_query_service,
        access_policy=media_access_policy,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
    )

    module = MediaModule(
        queries=media_queries,
        upload_service=media_upload_service,
        lifecycle_service=media_lifecycle_service,
        query_service=media_query_service,
        facade=facade,
        access_policy=media_access_policy,
    )

    admin_context = MediaAdminContext(
        queries=media_queries,
        delete_media_handler=delete_media_handler,
        reprocess_media_handler=reprocess_media_handler,
    )

    return module, admin_context


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "build_media_components",
]
