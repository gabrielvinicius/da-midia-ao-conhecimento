from __future__ import annotations

import asyncio
from enum import Enum
from typing import List
from unittest.mock import AsyncMock

import pytest

from src.shared.events.domain_events import MediaUploaded
from src.shared.events.async_queue_publisher import AsyncQueueBrokerPublisher
from src.shared.events.event_bus import EventBus, create_inmemory_event_bus
from src.shared.events.event_publisher import EventPublisher
from src.shared.events.subscription_manager import SubscriptionManager


@pytest.mark.asyncio
async def test_publish_dispatches_payload_to_subscribers():
    publisher = EventPublisher()
    subscriptions = SubscriptionManager()
    event_bus = EventBus(publisher=publisher, subscription_manager=subscriptions)

    received: List[MediaUploaded] = []

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

    received: List[MediaUploaded] = []

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


class MockBrokerPublisher:
    def __init__(self) -> None:
        self.publish_mock = AsyncMock()
        self.start_mock = AsyncMock(side_effect=self._start)
        self.stop_mock = AsyncMock(side_effect=self._stop)
        self._listener = None
        self._is_running = False

    async def _start(self, listener):
        self._listener = listener
        self._is_running = True

    async def _stop(self):
        self._listener = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def publish(self, event):
        await self.publish_mock(event)

    async def start(self, listener):
        await self.start_mock(listener)

    async def stop(self):
        await self.stop_mock()

    async def emit(self, event):
        if self._listener is None:
            raise RuntimeError("Listener not started")
        await self._listener(event)


@pytest.mark.asyncio
async def test_event_bus_with_mock_publisher_flows_events():
    publisher = MockBrokerPublisher()
    event_bus = EventBus(publisher=publisher, subscription_manager=SubscriptionManager())

    events: List[MediaUploaded] = []

    async def handler(event):
        events.append(event)

    event_bus.subscribe(MediaUploaded, handler)

    await event_bus.start_listener()
    assert event_bus.is_listening is True
    publisher.start_mock.assert_awaited_once()

    class DummyMediaType(Enum):
        AUDIO = "AUDIO"

    event = MediaUploaded(
        media_id="mock-001",
        user_id="user-123",
        media_type=DummyMediaType.AUDIO,
        file_path="/tmp/audio.mp3",
        storage_provider="local",
    )

    await event_bus.publish(event)
    publisher.publish_mock.assert_awaited_once_with(event)

    await publisher.emit(event)

    assert events and events[0].media_id == "mock-001"

    await event_bus.stop_listener()
    publisher.stop_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_inmemory_event_bus_returns_fresh_instances():
    first = create_inmemory_event_bus()
    second = create_inmemory_event_bus()

    assert first is not second


@pytest.mark.asyncio
async def test_create_inmemory_event_bus_start_stop_cycle():
    event_bus = create_inmemory_event_bus()

    assert event_bus.is_listening is False

    await event_bus.start_listener()
    assert event_bus.is_listening is True

    await event_bus.stop_listener()
    assert event_bus.is_listening is False


@pytest.mark.asyncio
async def test_async_queue_publisher_processes_events():
    publisher = AsyncQueueBrokerPublisher()
    event_bus = EventBus(
        publisher=publisher,
        subscription_manager=SubscriptionManager(),
    )

    processed = asyncio.Event()
    received: List[MediaUploaded] = []

    async def handler(event):
        received.append(event)
        processed.set()

    event_bus.subscribe(MediaUploaded, handler)
    await event_bus.start_listener()

    class DummyMediaType(Enum):
        AUDIO = "AUDIO"

    event = MediaUploaded(
        media_id="queue-123",
        user_id="user-999",
        media_type=DummyMediaType.AUDIO,
        file_path="/tmp/audio.mp3",
        storage_provider="local",
    )

    await event_bus.publish(event)
    await asyncio.wait_for(processed.wait(), timeout=1)

    assert received and received[0].media_id == "queue-123"

    await event_bus.stop_listener()

