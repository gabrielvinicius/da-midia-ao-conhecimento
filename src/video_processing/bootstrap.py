# src/video_processing/bootstrap.py
from typing import Dict, Any

from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from .application.commands.process_video_command_handler import ProcessVideoCommandHandler

def bootstrap_video_processing_module(
    media_queries: MediaQueries,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
) -> Dict[str, Any]:
    """Constructs and returns the services for the video_processing module."""
    process_video_handler = ProcessVideoCommandHandler(
        media_queries=media_queries,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus
    )
    return {
        "process_video_handler": process_video_handler
    }
