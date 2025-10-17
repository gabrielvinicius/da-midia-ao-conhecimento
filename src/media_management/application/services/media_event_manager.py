# src/media_management/application/services/media_event_manager.py
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import MediaUploaded
from src.media_management.domain.media import Media


class MediaEventManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def publish_media_uploaded(self, media: Media) -> None:
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(media.user_id),
            media_type=media.media_type,
            file_path=media.original_file_path,
            storage_provider=media.storage_provider,
            transcription_provider=media.transcription_provider,
            summarization_provider=media.summarization_provider,
        )
        await self.event_bus.publish(event)
