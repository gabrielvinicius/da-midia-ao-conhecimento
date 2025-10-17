# src/summarization/application/services/summary_notification_service.py
import json
import structlog
from pydantic import BaseModel

from src.notifications.infrastructure.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class SummaryNotificationService:
    """Handles sending real-time notifications related to the summary process."""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def push_update(self, entity_name: str, entity: BaseModel, user_id: str):
        """Pushes an entity update to the user via WebSocket."""
        try:
            message = {
                "type": "entity_update",
                "entity": entity_name,
                "payload": json.loads(entity.model_dump_json())
            }
            await self.connection_manager.send_personal_message(json.dumps(message), user_id)
            logger.info(f"{entity_name}.pushed_realtime_update", id=str(entity.id), user_id=user_id)
        except Exception as e:
            logger.error("notification.push.failed", entity_id=str(entity.id), user_id=user_id, error=str(e))
