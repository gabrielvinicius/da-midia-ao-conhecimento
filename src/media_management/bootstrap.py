# src/media_management/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.metrics.application.metrics_service import MetricsService

# Application Services
from src.media_management.application.queries.media_queries import MediaQueries

# Command Handlers
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.application.commands.delete_media_command_handler import DeleteMediaCommandHandler
from src.media_management.application.commands.reprocess_media_command_handler import ReprocessMediaCommandHandler

# Enhanced SOLID Services
from src.media_management.application.services.media_validator import MediaValidator
from src.media_management.application.services.media_uploader import MediaUploader
from src.media_management.application.services.media_factory import MediaFactory
from src.media_management.application.services.media_event_manager import MediaEventManager
from src.media_management.application.services.media_metrics_service import MediaMetricsService
from src.media_management.application.services.media_storage_manager import MediaStorageManager
from src.media_management.application.services.media_state_service import MediaStateService
from src.media_management.application.services.media_authorization_service import MediaAuthorizationService

# New SOLID Services
from src.media_management.application.services.enhanced_media_validator import EnhancedMediaValidator
from src.media_management.application.services.enhanced_media_metrics_service import EnhancedMediaMetricsService
from src.media_management.application.services.media_state_manager import MediaStateManager
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.infrastructure.cache import CacheService

# Infrastructure & Config
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.config.settings import MediaSettings

def bootstrap_media_module(
    db_session: AsyncSession,
    storage_service_factory: StorageServiceFactory,
    event_bus: EventBus,
    metrics_service: MetricsService,
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
) -> Dict[str, Any]:
    """Constructs and returns the services for the media_management module."""
    media_repository = MediaRepository(db=db_session)
    media_queries = MediaQueries(media_repository=media_repository)
    media_settings = MediaSettings()

    # --- SOLID Services (Following SRP) ---
    enhanced_media_validator = EnhancedMediaValidator(
        max_file_size=100 * 1024 * 1024,  # 100MB
        min_file_size=1024  # 1KB
    )
    
    enhanced_media_metrics = EnhancedMediaMetricsService(
        metrics_collector=metrics_collector
    )
    
    media_state_manager = MediaStateManager(
        cache_service=cache_service
    )
    
    # --- Legacy Services (for backward compatibility) ---
    media_validator = MediaValidator(settings=media_settings)
    media_uploader = MediaUploader(storage_service_factory=storage_service_factory)
    media_factory = MediaFactory()
    media_event_manager = MediaEventManager(event_bus=event_bus)
    media_metrics = MediaMetricsService(metrics_provider=None)  # Legacy
    media_storage_manager = MediaStorageManager(storage_service_factory=storage_service_factory)
    media_state_service = MediaStateService()
    media_authorization_service = MediaAuthorizationService()

    # Instantiate command handlers with new dependencies
    create_media_handler = CreateMediaCommandHandler(
        media_repository=media_repository,
        media_validator=media_validator,
        media_uploader=media_uploader,
        media_factory=media_factory,
        media_event_manager=media_event_manager,
        media_metrics_service=media_metrics,
    )
    delete_media_handler = DeleteMediaCommandHandler(
        media_repository=media_repository,
        media_queries=media_queries,
        media_storage_manager=media_storage_manager,
    )
    reprocess_media_handler = ReprocessMediaCommandHandler(
        media_queries=media_queries,
        media_repository=media_repository,
        media_state_service=media_state_service,
        media_event_manager=media_event_manager,
    )

    return {
        # Infrastructure
        "media_repository": media_repository,
        "media_queries": media_queries,
        "media_settings": media_settings,
        
        # Enhanced SOLID Services
        "enhanced_media_validator": enhanced_media_validator,
        "enhanced_media_metrics": enhanced_media_metrics,
        "media_state_manager": media_state_manager,
        
        # Command Handlers
        "create_media_handler": create_media_handler,
        "delete_media_handler": delete_media_handler,
        "reprocess_media_handler": reprocess_media_handler,
        
        # Legacy Services (backward compatibility)
        "media_validator": media_validator,
        "media_uploader": media_uploader,
        "media_factory": media_factory,
        "media_event_manager": media_event_manager,
        "media_metrics": media_metrics,
        "media_storage_manager": media_storage_manager,
        "media_state_service": media_state_service,
        "media_authorization_service": media_authorization_service,
    }
