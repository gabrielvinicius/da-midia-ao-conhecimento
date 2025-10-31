"""Event system scaffolding exposed for application modules."""

from .bus import InMemoryEventBus, SupportsEventBus, EventCallback
from .domain_events import DomainEvent, MediaUploaded, TextContentReady

__all__ = [
    "EventCallback",
    "DomainEvent",
    "InMemoryEventBus",
    "MediaUploaded",
    "SupportsEventBus",
    "TextContentReady",
]
