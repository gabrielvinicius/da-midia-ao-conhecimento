# src/text_processing/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from .application.commands.process_text_command_handler import ProcessTextCommandHandler

def bootstrap_text_processing_module(
    db_session: AsyncSession,
    media_queries: MediaQueries,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
) -> Dict[str, Any]:
    """Constructs and returns the services for the text_processing module."""
    # The handler needs its own instance of the media repository to save state changes
    media_repository = MediaRepository(db=db_session)
    
    process_text_handler = ProcessTextCommandHandler(
        media_queries=media_queries,
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus
    )
    return {
        "process_text_handler": process_text_handler
    }
