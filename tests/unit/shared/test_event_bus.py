from enum import Enum

import pytest
from src.shared.events.domain_events import MediaUploaded
from src.shared.events.event_bus import EventBus
from src.shared.events.event_publisher import EventPublisher
from src.shared.events.subscription_manager import SubscriptionManager


@pytest.mark.asyncio
async def test_publish_dispatches_payload_to_subscribers():
    publisher = EventPublisher()
    subscriptions = SubscriptionManager()
    event_bus = EventBus(publisher=publisher, subscription_manager=subscriptions)

    received = []

    async def handler(event):
        received.append(event)

    event_bus.subscribe(MediaUploaded, handler)

    class DummyMediaType(Enum):
        AUDIO = "AUDIO"

    event = MediaUploaded(
        media_id="media-123",
        user_id="user-456",
        media_type=DummyMediaType.AUDIO,
        file_path="/tmp/audio.mp3",
        storage_provider="local",
    )

    await event_bus.publish(event)

    assert len(received) == 1
    event_received = received[0]
    assert event_received.media_id == "media-123"
    assert event_received.media_type is DummyMediaType.AUDIO
    assert event_received.event_name == "media_uploaded"


@pytest.mark.asyncio
async def test_start_listener_processes_incoming_events():
    publisher = EventPublisher()
    event_bus = EventBus(publisher=publisher)

    received = []

    async def handler(event):
        received.append(event)

    event_bus.subscribe(MediaUploaded, handler)

    await event_bus.start_listener()
    assert event_bus.is_listening is True

    class DummyMediaType(Enum):
        AUDIO = "AUDIO"
        VIDEO = "VIDEO"

    incoming_event = MediaUploaded(
        media_id="media-999",
        user_id="user-999",
        media_type=DummyMediaType.VIDEO,
        file_path="/tmp/video.mp4",
        storage_provider="s3",
    )

    await publisher.emit(incoming_event)

    assert len(received) == 1
    assert received[0].media_type is DummyMediaType.VIDEO

