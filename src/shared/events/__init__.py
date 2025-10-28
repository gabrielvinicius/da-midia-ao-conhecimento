"""Shared event system exports."""

from .domain_events import DomainEvent
from .event_bus import EventBus
from .event_publisher import EventPublisher, EventHandler
from .subscription_manager import SubscriptionManager

__all__ = [
    "DomainEvent",
    "EventBus",
    "EventPublisher",
    "EventHandler",
    "SubscriptionManager",
]
"""Event bus abstractions and domain event definitions."""

from . import domain_events
from .domain_events import *  # noqa: F401,F403 - re-export domain events
from .event_bus import EventBus
from .event_publisher import EventPublisher
from .subscription_manager import SubscriptionManager

__all__ = ["EventBus", "EventPublisher", "SubscriptionManager"] + list(domain_events.__all__)
