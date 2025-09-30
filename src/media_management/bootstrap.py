# src/media_management/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.metrics.application.metrics_service import MetricsService
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.application.commands.delete_media_command_handler import DeleteMediaCommandHandler # Import new handler
from src.media_management.application.media_service import MediaService
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository

def bootstrap_media_module(
    db_session: AsyncSession,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
    metrics_service: MetricsService,
) -> Dict[str, Any]:
    """Constructs and returns the services for the media_management module."""
    media_repository = MediaRepository(db=db_session)
    media_queries = MediaQueries(media_repository=media_repository)
    
    # Instantiate all command handlers
    create_media_handler = CreateMediaCommandHandler(
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus,
        metrics_service=metrics_service
    )
    delete_media_handler = DeleteMediaCommandHandler(
        media_repository=media_repository,
        media_queries=media_queries,
        storage_service_factory=storage_service_factory
    )

    # Instantiate the facade service with all handlers
    media_service = MediaService(
        create_media_handler=create_media_handler,
        delete_media_handler=delete_media_handler # Inject new handler
    )

    return {
        "media_repository": media_repository,
        "media_queries": media_queries,
        "media_service": media_service,
    }
