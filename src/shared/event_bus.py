"""Convenience module exposing the default event bus implementation."""
from __future__ import annotations

from src.shared.events.bus import EventCallback, InMemoryEventBus, SupportsEventBus
from src.shared.events.domain_events import DomainEvent

__all__ = [
    "DomainEvent",
    "EventCallback",
    "InMemoryEventBus",
    "SupportsEventBus",
]
