"""Lightweight event bus abstraction with in-memory implementation."""
from __future__ import annotations

from collections import defaultdict
from typing import (
    Awaitable,
    Callable,
    DefaultDict,
    Iterable,
    List,
    Protocol,
    Type,
    TypeVar,
)

from src.shared.events.domain_events import DomainEvent

EventCallback = Callable[[DomainEvent], Awaitable[None]]
TEvent = TypeVar("TEvent", bound=DomainEvent)


class SupportsEventBus(Protocol):
    """Protocol defining the contract expected from an event bus implementation."""

    async def publish(self, event: DomainEvent) -> None:  # pragma: no cover - protocol definition
        ...

    async def publish_many(self, events: Iterable[DomainEvent]) -> None:  # pragma: no cover
        ...

    def subscribe(self, event_type: Type[TEvent], handler: EventCallback) -> None:  # pragma: no cover
        ...

    def unsubscribe(self, event_type: Type[TEvent], handler: EventCallback) -> None:  # pragma: no cover
        ...

    async def start_listener(self) -> None:  # pragma: no cover
        ...

    async def stop_listener(self) -> None:  # pragma: no cover
        ...


class InMemoryEventBus:
    """Simple asynchronous event bus used during Stage A scaffolding and tests."""

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[Type[DomainEvent], List[EventCallback]] = defaultdict(list)
        self._started: bool = False

    async def publish(self, event: DomainEvent) -> None:
        """Deliver an event to every registered handler."""
        handlers = list(self._subscriptions.get(type(event), []))
        for handler in handlers:
            await handler(event)

    async def publish_many(self, events: Iterable[DomainEvent]) -> None:
        """Publish a batch of events preserving order."""
        for event in events:
            await self.publish(event)

    def subscribe(self, event_type: Type[TEvent], handler: EventCallback) -> None:
        """Register an asynchronous handler for the given event."""
        self._subscriptions[event_type].append(handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventCallback) -> None:
        """Unregister an event handler."""
        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:  # pragma: no cover - defensive guard
            pass

    def has_subscribers(self, event_type: Type[DomainEvent]) -> bool:
        """Utility used in smoke tests to confirm registration."""
        return bool(self._subscriptions.get(event_type))

    async def start_listener(self) -> None:
        """Hook invoked during application startup to activate the bus."""
        self._started = True

    async def stop_listener(self) -> None:
        """Hook invoked during shutdown to flush subscriptions."""
        self._subscriptions.clear()
        self._started = False


__all__ = [
    "EventCallback",
    "InMemoryEventBus",
    "SupportsEventBus",
]
