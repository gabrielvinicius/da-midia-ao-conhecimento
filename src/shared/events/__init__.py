"""Event system scaffolding exposed for application modules."""

from .async_queue_publisher import AsyncQueueBrokerPublisher
from .bus import InMemoryEventBus, SupportsEventBus, EventCallback
from .domain_events import DomainEvent, MediaDeleted, MediaReprocessRequested, MediaUploaded, TextContentReady
from .event_bus import EventBus, create_inmemory_event_bus
from .event_publisher import EventPublisher
from .subscription_manager import SubscriptionManager

__all__ = [
    "AsyncQueueBrokerPublisher",
    "EventCallback",
    "EventBus",
    "DomainEvent",
    "EventPublisher",
    "InMemoryEventBus",
    "MediaDeleted",
    "MediaReprocessRequested",
    "MediaUploaded",
    "SupportsEventBus",
    "SubscriptionManager",
    "TextContentReady",
    "create_inmemory_event_bus",
]
