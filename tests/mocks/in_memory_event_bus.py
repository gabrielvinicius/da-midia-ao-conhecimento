# tests/mocks/in_memory_event_bus.py
"""Lightweight in-memory event bus used in tests."""

from __future__ import annotations

from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, List, Type

from src.shared.events.domain_events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InMemoryEventBus:
    """Minimal event bus that stores published events in memory."""

    def __init__(self) -> None:
        self.events: List[DomainEvent] = []
        self._subscriptions: DefaultDict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._subscriptions[event_type].append(handler)

    def unsubscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:  # pragma: no cover - defensive guard
            pass

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)
        handlers = list(self._subscriptions.get(type(event), []))
        for handler in handlers:
            await handler(event)

    def get_events(self, event_type: Type[DomainEvent]) -> List[DomainEvent]:
        return [event for event in self.events if isinstance(event, event_type)]

    def clear(self) -> None:
        self.events.clear()
        self._subscriptions.clear()
