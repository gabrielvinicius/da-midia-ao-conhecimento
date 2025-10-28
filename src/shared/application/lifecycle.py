"""Helpers that encapsulate application lifecycle orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.events.event_bus import EventBus
from src.video_processing.bootstrap import VideoProcessingEventContext
from src.text_processing.bootstrap import TextProcessingEventContext
from src.transcription.bootstrap import TranscriptionEventContext
from src.summarization.bootstrap import SummarizationEventContext

from src.video_processing.application.event_handlers import (
    register_event_handlers as register_video_handlers,
)
from src.text_processing.application.event_handlers import (
    register_event_handlers as register_text_handlers,
)
from src.transcription.application.event_handlers import (
    register_event_handlers as register_transcription_handlers,
)
from src.summarization.application.event_handlers import (
    register_event_handlers as register_summary_handlers,
)
from src.notifications.application.event_handlers import (
    register_event_handlers as register_notification_handlers,
)
from src.sentiment_analysis.application.event_handlers import (
    register_event_handlers as register_sentiment_handlers,
)
from src.topic_modeling.application.event_handlers import (
    register_event_handlers as register_topic_handlers,
)


class CacheClient(Protocol):
    """Minimal cache protocol used during application bootstrap."""

    async def connect(self) -> None:  # pragma: no cover - protocol definition
        ...

    async def disconnect(self) -> None:  # pragma: no cover - protocol definition
        ...


@dataclass
class ApplicationResources:
    """Infrastructure resources that require explicit lifecycle management."""

    event_bus: EventBus
    cache: CacheClient


@dataclass
class EventHandlersConfig:
    """Dependencies required to register all domain event handlers."""

    event_bus: EventBus
    media_queries: MediaQueries
    video: VideoProcessingEventContext
    text: TextProcessingEventContext
    transcription: TranscriptionEventContext
    summarization: SummarizationEventContext


async def start_application_resources(resources: ApplicationResources) -> None:
    """Initialize long-lived infrastructure resources."""

    await resources.event_bus.start_listener()
    await resources.cache.connect()


async def stop_application_resources(resources: ApplicationResources) -> None:
    """Gracefully release infrastructure resources."""

    await resources.cache.disconnect()
    await resources.event_bus.stop_listener()


async def register_event_handlers(config: EventHandlersConfig) -> None:
    """Register all module event handlers in a centralised manner."""

    await register_video_handlers(config.event_bus, config.video.task_scheduler)
    await register_text_handlers(config.event_bus, config.text.task_scheduler)
    await register_transcription_handlers(
        config.event_bus,
        config.transcription.repository,
        config.media_queries,
    )
    await register_summary_handlers(
        config.event_bus,
        config.summarization.repository,
        config.media_queries,
        config.summarization.task_scheduler,
    )
    await register_notification_handlers(config.event_bus)
    await register_sentiment_handlers(config.event_bus)
    await register_topic_handlers(config.event_bus)


__all__ = [
    "ApplicationResources",
    "EventHandlersConfig",
    "register_event_handlers",
    "start_application_resources",
    "stop_application_resources",
]
