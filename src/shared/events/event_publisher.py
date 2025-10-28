"""Utility responsible for dispatching events to subscribed handlers."""
from __future__ import annotations

import asyncio
from typing import Iterable, Protocol, runtime_checkable

from .domain_events import DomainEvent


@runtime_checkable
class EventHandler(Protocol):
    async def __call__(self, event: DomainEvent) -> None:  # pragma: no cover - Protocol definition
        ...


def _is_awaitable(result: object) -> bool:
    """Return True when the handler result is awaitable."""
    return asyncio.iscoroutine(result) or isinstance(result, asyncio.Future)


class EventPublisher:
    """Executes handlers registered for a domain event."""

    async def publish(self, event: DomainEvent, handlers: Iterable[EventHandler]) -> None:
        for handler in handlers:
            result = handler(event)
            if _is_awaitable(result):
                await result


__all__ = ["EventPublisher", "EventHandler"]
"""Infrastructure-agnostic event publisher abstraction."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from .domain_events import DomainEvent

IncomingEventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher:
    """Coordinates communication with the underlying message broker.

    The default implementation is intentionally minimal; it simply records the
    consumer callback and exposes :meth:`emit` to simulate external events.
    Concrete implementations can extend this class to integrate with Redis,
    RabbitMQ, or any other broker without changing the application layer.
    """

    def __init__(self) -> None:
        self._listener: Optional[IncomingEventHandler] = None
        self._is_running = False

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to the broker.

        The base implementation is a no-op; subclasses should override this
        method to forward the event to an external system.  The event bus still
        dispatches events locally to in-memory subscribers.
        """

    async def start(self, on_event: IncomingEventHandler) -> None:
        """Register a callback to receive events from the broker."""

        self._listener = on_event
        self._is_running = True

    async def stop(self) -> None:
        """Stop consuming events from the broker."""

        self._listener = None
        self._is_running = False

    async def emit(self, event: DomainEvent) -> None:
        """Simulate the arrival of ``event`` from the broker."""

        if self._listener is None:
            return
        await self._listener(event)

    @property
    def is_running(self) -> bool:
        """Return ``True`` when the publisher is actively listening."""

        return self._is_running


__all__ = ["EventPublisher", "IncomingEventHandler"]

