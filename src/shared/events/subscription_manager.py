"""Subscription management for the domain event bus."""
from __future__ import annotations

from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, Dict, List, Type, Union

from .domain_events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]
EventKey = Union[str, Type[DomainEvent]]


class SubscriptionManager:
    """Keeps track of event handlers registered for each domain event."""

    def __init__(self) -> None:
        self._by_type: DefaultDict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)
        self._by_name: DefaultDict[str, List[EventHandler]] = defaultdict(list)

    def _select_bucket(self, event: EventKey) -> List[EventHandler]:
        if isinstance(event, str):
            return self._by_name[event]
        return self._by_type[event]

    def add_subscription(self, event: EventKey, handler: EventHandler) -> None:
        """Register ``handler`` for ``event`` if not already registered."""

        bucket = self._select_bucket(event)
        if handler not in bucket:
            bucket.append(handler)

    def remove_subscription(self, event: EventKey, handler: EventHandler) -> None:
        """Remove ``handler`` from ``event`` subscriptions."""

        bucket = self._select_bucket(event)
        try:
            bucket.remove(handler)
        except ValueError:
            return
        if not bucket:
            if isinstance(event, str):
                del self._by_name[event]
            else:
                del self._by_type[event]

    def get_handlers(self, event: EventKey) -> List[EventHandler]:
        """Return the handlers registered for ``event``."""

        if isinstance(event, str):
            return list(self._by_name.get(event, []))
        return list(self._by_type.get(event, []))

    def has_subscribers(self, event: EventKey) -> bool:
        """Return ``True`` when ``event`` has at least one handler."""

        return bool(self.get_handlers(event))

    def clear(self) -> None:
        """Remove all registered subscriptions."""

        self._by_type.clear()
        self._by_name.clear()


__all__ = ["SubscriptionManager", "EventHandler", "EventKey"]
