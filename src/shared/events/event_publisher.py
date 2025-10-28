"""Infrastructure-agnostic event publisher abstraction."""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from .domain_events import DomainEvent

IncomingEventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher:
    """Coordinates communication with the underlying message broker."""

    def __init__(self) -> None:
        self._listener: Optional[IncomingEventHandler] = None
        self._is_running = False

    async def publish(self, event: DomainEvent) -> None:  # pragma: no cover - default no-op
        """Publish an event to the broker.

        Concrete implementations can override this method to forward events to
        external systems. The in-memory event bus still dispatches events to
        local subscribers immediately.
        """

    async def start(self, on_event: IncomingEventHandler) -> None:
        """Register a callback to receive events from the broker."""

        self._listener = on_event
        self._is_running = True

    async def stop(self) -> None:
        """Stop consuming events from the underlying broker."""

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
