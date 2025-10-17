# src/notifications/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.auth.application.queries.auth_queries import AuthQueries
from src.shared.events.event_bus import EventBus
from src.notifications.application.commands.request_notification_command_handler import RequestNotificationCommandHandler
from src.notifications.application.queries.notification_queries import NotificationQueries
from src.notifications.application.notification_service import LegacyNotificationService
from src.notifications.application.services.notification_service import NotificationService
from src.notifications.application.services.notification_delivery_service import NotificationDeliveryService
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.infrastructure.connection_manager import connection_manager

def bootstrap_notification_module(
    db_session: AsyncSession,
    auth_queries: AuthQueries, # Correct cross-context dependency
    event_bus: EventBus,
) -> Dict[str, Any]:
    """
    Constructs and returns the services for the notification module following SOLID principles.
    
    All services depend on interfaces for maximum flexibility and testability.
    """
    # Repository (implements INotificationRepository)
    notification_repository = NotificationRepository(db=db_session)
    
    # Legacy command handler and queries
    request_notification_handler = RequestNotificationCommandHandler(
        auth_queries=auth_queries,
        event_bus=event_bus
    )
    
    notification_queries = NotificationQueries(notification_repository=notification_repository)
    
    # WebSocket manager (implements IWebSocketManager)
    websocket_manager = connection_manager
    
    # Placeholder services (would be implemented with real providers)
    # For now, using None to show the interface structure
    email_sender = None  # Would be EmailSender(smtp_config)
    sms_sender = None    # Would be SMSSender(sms_config)
    push_sender = None   # Would be PushSender(push_config)
    
    # Preferences service (placeholder - would implement INotificationPreferences)
    preferences_service = None  # Would be NotificationPreferencesService(db_session)
    
    # Queue service (placeholder - would implement INotificationQueue)
    queue_service = None  # Would be NotificationQueueService(redis_config)
    
    # Delivery service
    delivery_service = NotificationDeliveryService(
        preferences_service=preferences_service,
        websocket_manager=websocket_manager,
        email_sender=email_sender,
        sms_sender=sms_sender,
        push_sender=push_sender
    )
    
    # Main notification service
    notification_service = NotificationService(
        notification_repository=notification_repository,
        delivery_service=delivery_service,
        preferences_service=preferences_service,
        queue_service=queue_service
    )
    
    # Legacy service for backward compatibility
    legacy_notification_service = LegacyNotificationService(
        notification_repository=notification_repository
    )

    return {
        # Legacy services for backward compatibility
        "request_notification_handler": request_notification_handler,
        "notification_queries": notification_queries,
        
        # New SOLID services
        "notification_repository": notification_repository,
        "notification_service": notification_service,
        "legacy_notification_service": legacy_notification_service,
        "delivery_service": delivery_service,
        "websocket_manager": websocket_manager,
        "connection_manager": connection_manager,  # Legacy compatibility
    }
