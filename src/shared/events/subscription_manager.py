"""Manage event subscriptions for the shared event bus."""
from __future__ import annotations

from collections import defaultdict
from typing import List, MutableMapping, Union

from .domain_events import DomainEvent
from .event_publisher import EventHandler

EventKey = Union[str, type[DomainEvent]]


class SubscriptionManager:
    """Register and look up handlers for published events."""

    def __init__(self) -> None:
        self._handlers: MutableMapping[str, List[EventHandler]] = defaultdict(list)

    @staticmethod
    def _normalise_key(event: EventKey) -> str:
        if isinstance(event, str):
            return event
        return event.__name__

    def add_subscription(self, event: EventKey, handler: EventHandler) -> None:
        key = self._normalise_key(event)
        if handler not in self._handlers[key]:
            self._handlers[key].append(handler)

    def remove_subscription(self, event: EventKey, handler: EventHandler) -> None:
        key = self._normalise_key(event)
        handlers = self._handlers.get(key)
        if not handlers:
            return
        if handler in handlers:
            handlers.remove(handler)
        if not handlers:
            self._handlers.pop(key, None)

    def get_handlers(self, event: EventKey) -> List[EventHandler]:
        key = self._normalise_key(event)
        return list(self._handlers.get(key, []))

    def has_subscribers(self, event: EventKey) -> bool:
        return bool(self.get_handlers(event))

    def clear(self) -> None:
        self._handlers.clear()


__all__ = ["SubscriptionManager", "EventKey"]
