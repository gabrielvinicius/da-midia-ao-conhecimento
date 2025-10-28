"""Public exports for the shared event system."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .domain_events import DomainEvent

__all__ = [
    "DomainEvent",
    "EventBus",
    "EventPublisher",
    "EventHandler",
    "SubscriptionManager",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - lazy import helper
    if name == "EventBus":
        return import_module(".event_bus", __name__).EventBus
    if name == "EventPublisher":
        module = import_module(".event_publisher", __name__)
        return module.EventPublisher
    if name == "EventHandler":
        module = import_module(".subscription_manager", __name__)
        return module.EventHandler
    if name == "SubscriptionManager":
        module = import_module(".subscription_manager", __name__)
        return module.SubscriptionManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
