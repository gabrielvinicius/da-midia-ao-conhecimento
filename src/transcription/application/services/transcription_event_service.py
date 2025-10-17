# src/transcription/application/services/transcription_event_service.py
from src.shared.events.domain_events import TextContentReady, ProcessingFailed
from src.shared.events.event_bus import EventBus


class TranscriptionEventService:
    """Handles the publishing of events related to the transcription process."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def publish_completion_event(self, media_id: str, text_content: str):
        """Publishes an event indicating that transcription has successfully completed."""
        event = TextContentReady(media_id=media_id, text_content=text_content)
        await self.event_bus.publish(event)

    async def publish_failure_event(self, media_id: str, error: str):
        """Publishes an event indicating that transcription has failed."""
        event = ProcessingFailed(media_id=media_id, error=error)
        await self.event_bus.publish(event)
