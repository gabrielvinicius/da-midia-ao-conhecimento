"""
Unified notification service - eliminating notification duplication
"""
import json
import structlog
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)

class UnifiedNotificationService:
    """Single notification service for all domains - eliminating duplication"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_operation_started(
        self, 
        user_id: str, 
        entity_type: str,  # transcription, summary, etc.
        entity_id: str, 
        operation_type: str,  # started, progress, completed, failed
        message: str,
        payload: Dict[str, Any] = None
    ) -> None:
        """Universal notification method"""
        await self._send_notification(
            user_id=user_id,
            notification_type=f"{entity_type}_{operation_type}",
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
            payload=payload or {}
        )
    
    async def notify_progress(
        self, 
        user_id: str, 
        entity_type: str, 
        entity_id: str, 
        progress: float,
        message: Optional[str] = None
    ) -> None:
        """Universal progress notification"""
        await self.notify_operation_started(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_type="progress",
            message=message or f"{entity_type.title()} progress: {progress:.1%}",
            payload={"progress": progress}
        )
    
    async def notify_completed(
        self, 
        user_id: str, 
        entity_type: str, 
        entity_id: str, 
        result: Dict[str, Any],
        message: Optional[str] = None
    ) -> None:
        """Universal completion notification"""
        await self.notify_operation_started(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_type="completed",
            message=message or f"{entity_type.title()} completed successfully",
            payload=result
        )
    
    async def notify_failed(
        self, 
        user_id: str, 
        entity_type: str, 
        entity_id: str, 
        error: str,
        message: Optional[str] = None
    ) -> None:
        """Universal failure notification"""
        await self.notify_operation_started(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation_type="failed",
            message=message or f"{entity_type.title()} failed: {error}",
            payload={"error": error}
        )
    
    async def _send_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        entity_type: str,
        entity_id: str,
        message: str,
        payload: Dict[str, Any]
    ) -> None:
        """Internal notification sender"""
        try:
            notification_payload = {
                "type": notification_type,
                "entity": entity_type,
                "message": message,
                "payload": {
                    "entity_id": entity_id,
                    **payload
                }
            }
            
            await self._connection_manager.send_personal_message(
                json.dumps(notification_payload), 
                user_id
            )
            
            logger.info(
                "notification.sent",
                type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(
                "notification.failed",
                type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                error=str(e)
            )

class NoOpNotificationService(UnifiedNotificationService):
    """No-op implementation for testing"""
    
    def __init__(self):
        pass  # No connection manager needed
    
    async def _send_notification(self, *args, **kwargs) -> None:
        """No-op implementation"""
        pass