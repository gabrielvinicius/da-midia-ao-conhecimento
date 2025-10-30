"""Utilities to manage event bus subscriptions."""
from __future__ import annotations

from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, Iterable, List, Type, TypeVar

from src.shared.events.domain_events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]
TEvent = TypeVar("TEvent", bound=DomainEvent)


class SubscriptionManager:
    """Keeps track of event handlers registered for each event type."""

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Register an asynchronous handler for a given event type."""

        handlers = self._subscriptions[event_type]
        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Remove a previously registered handler."""

        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return

        try:
            handlers.remove(handler)
        except ValueError:  # pragma: no cover - defensive guard
            return

        if not handlers:
            self._subscriptions.pop(event_type, None)

    def handlers_for(self, event_type: Type[TEvent]) -> Iterable[EventHandler]:
        """Return handlers for the provided event type."""

        return tuple(self._subscriptions.get(event_type, ()))

    def clear(self) -> None:
        """Remove all registered handlers (used when stopping the bus)."""

        self._subscriptions.clear()


__all__ = ["SubscriptionManager", "EventHandler"]
