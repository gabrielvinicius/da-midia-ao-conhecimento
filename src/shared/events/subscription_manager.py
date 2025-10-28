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

