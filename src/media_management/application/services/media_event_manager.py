# src/media_management/application/services/media_event_manager.py
from src.media_management.domain.media import Media
from src.media_processing.tasks import process_media_task


class MediaEventManager:
    def __init__(self) -> None:
        pass

    async def publish_media_uploaded(self, media: Media) -> None:
        """Back-compat hook that now schedules Celery processing instead of events."""
        process_media_task.delay(media_id=str(media.id))
