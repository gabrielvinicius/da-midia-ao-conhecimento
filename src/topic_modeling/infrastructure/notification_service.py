# src/topic_modeling/infrastructure/notification_service.py
"""
Topic modeling notification service implementation - SRP compliance.
"""
import json
import structlog
from typing import Dict, Any, List

from src.topic_modeling.domain.interfaces import TopicModelingNotificationService
from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class WebSocketTopicModelingNotificationService(TopicModelingNotificationService):
    """
    WebSocket-based notification service for topic modeling operations.
    Follows SRP - only responsible for notifications.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self._connection_manager = connection_manager
    
    async def notify_started(self, media_id: str, user_id: str, provider: str) -> None:
        """Notify topic modeling started."""
        await self._send_notification(
            user_id=user_id,
            notification_type="topic_modeling_started",
            media_id=media_id,
            message=f"Topic modeling started using {provider}",
            payload={"provider": provider}
        )
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        topics: List[Dict[str, Any]]
    ) -> None:
        """Notify topic modeling completed."""
        num_topics = len(topics)
        
        # Calculate average coherence score
        coherence_scores = [topic.get("coherence_score", 0.0) for topic in topics]
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
        
        # Get top topic words for preview
        top_topics = []
        for i, topic in enumerate(topics[:3]):  # Show top 3 topics
            words = topic.get("words", [])[:5]  # Top 5 words
            top_topics.append({
                "topic_id": i + 1,
                "words": words
            })
        
        await self._send_notification(
            user_id=user_id,
            notification_type="topic_modeling_completed",
            media_id=media_id,
            message=f"Topic modeling completed: {num_topics} topics extracted",
            payload={
                "num_topics": num_topics,
                "avg_coherence": avg_coherence,
                "top_topics": top_topics
            }
        )
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify topic modeling failed."""
        await self._send_notification(
            user_id=user_id,
            notification_type="topic_modeling_failed",
            media_id=media_id,
            message=f"Topic modeling failed: {error}",
            payload={"error": error}
        )
    
    async def _send_notification(
        self, 
        user_id: str, 
        notification_type: str, 
        media_id: str,
        message: str,
        payload: Dict[str, Any] = None
    ) -> None:
        """Send notification via WebSocket."""
        try:
            notification_payload = {
                "type": notification_type,
                "entity": "topic_modeling",
                "message": message,
                "payload": {
                    "media_id": media_id,
                    **(payload or {})
                }
            }
            
            await self._connection_manager.send_personal_message(
                json.dumps(notification_payload), 
                user_id
            )
            
            logger.info(
                "topic_modeling.notification.sent",
                type=notification_type,
                media_id=media_id,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(
                "topic_modeling.notification.failed",
                type=notification_type,
                media_id=media_id,
                user_id=user_id,
                error=str(e)
            )


class EmailTopicModelingNotificationService(TopicModelingNotificationService):
    """
    Email-based notification service for topic modeling operations.
    Alternative implementation following same interface.
    """
    
    def __init__(self, email_service):
        self._email_service = email_service
    
    async def notify_started(self, media_id: str, user_id: str, provider: str) -> None:
        """Notify topic modeling started via email."""
        # Implementation would send email
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        topics: List[Dict[str, Any]]
    ) -> None:
        """Notify topic modeling completed via email."""
        # Implementation would send email with topic summary
        pass
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify topic modeling failed via email."""
        # Implementation would send error email
        pass


class NoOpTopicModelingNotificationService(TopicModelingNotificationService):
    """
    No-operation notification service for testing.
    Follows Null Object pattern.
    """
    
    async def notify_started(self, media_id: str, user_id: str, provider: str) -> None:
        """No-op implementation."""
        pass
    
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        topics: List[Dict[str, Any]]
    ) -> None:
        """No-op implementation."""
        pass
    
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """No-op implementation."""
        pass