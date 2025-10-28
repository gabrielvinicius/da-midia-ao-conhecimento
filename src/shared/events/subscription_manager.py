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
"""Subscription management for the domain event bus."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict, Dict, List, Type

from .domain_events import DomainEvent

EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class SubscriptionManager:
    """Keeps track of event handlers registered for each domain event."""

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)

    def add_subscription(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """Register ``handler`` for ``event_type`` if not already registered."""

        handlers = self._subscriptions[event_type]
        if handler not in handlers:
            handlers.append(handler)

    def remove_subscription(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """Remove ``handler`` from ``event_type`` subscriptions."""

        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return

        try:
            handlers.remove(handler)
        except ValueError:
            return

        if not handlers:
            del self._subscriptions[event_type]

    def get_handlers(self, event_type: Type[DomainEvent]) -> List[EventHandler]:
        """Return the list of handlers registered for ``event_type``."""

        return list(self._subscriptions.get(event_type, []))

    def clear(self) -> None:
        """Remove all registered subscriptions."""

        self._subscriptions.clear()

    def has_subscribers(self, event_type: Type[DomainEvent]) -> bool:
        """Return ``True`` when ``event_type`` has at least one handler."""

        return bool(self._subscriptions.get(event_type))


__all__ = ["SubscriptionManager", "EventHandler"]

