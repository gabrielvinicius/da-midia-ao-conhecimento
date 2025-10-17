# src/video_processing/bootstrap.py
from typing import Dict, Any

# Infrastructure & Config
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.events.event_bus import EventBus
from src.notifications.infrastructure.connection_manager import ConnectionManager

# Command Handlers
from src.video_processing.application.commands.process_video_command_handler import ProcessVideoCommandHandler

# SRP Services (Factories, Processors, etc.)
from src.video_processing.application.services.video_factory import VideoFactory
from src.video_processing.application.services.default_video_processor import DefaultVideoProcessor

# Specialized Services
from src.video_processing.application.services.video_notification_service import DefaultVideoNotificationService
from src.video_processing.application.services.video_orchestration_service import DefaultVideoOrchestrationService


def bootstrap_video_processing_module(
    media_queries: MediaQueries,
    media_repository: MediaRepository,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
    connection_manager: ConnectionManager,
) -> Dict[str, Any]:
    """Constructs and returns the services for the video_processing module following SOLID principles."""
    
    # --- SRP Services for Video Processing ---
    video_factory = VideoFactory()
    video_processor = DefaultVideoProcessor()
    
    # --- Specialized Services ---
    notification_service = DefaultVideoNotificationService(connection_manager=connection_manager)
    
    orchestration_service = DefaultVideoOrchestrationService(
        video_processor=video_processor,
        video_factory=video_factory,
        notification_service=notification_service
    )
    
    # --- Command Handlers ---
    process_video_handler = ProcessVideoCommandHandler(
        media_queries=media_queries,
        media_repository=media_repository,
        storage_service_factory=storage_service_factory,
        event_bus=event_bus,
        connection_manager=connection_manager
    )

    return {
        "video_factory": video_factory,
        "video_processor": video_processor,
        "notification_service": notification_service,
        "orchestration_service": orchestration_service,
        "process_video_handler": process_video_handler,
    }
