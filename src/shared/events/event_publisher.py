"""Event publishers used by the shared event bus."""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from src.shared.events.domain_events import DomainEvent

EventListener = Callable[[DomainEvent], Awaitable[None]]


class EventPublisher:
    """Lightweight publisher that directly forwards events to a listener."""

    def __init__(self) -> None:
        self._listener: Optional[EventListener] = None
        self._running: bool = False

    async def publish(self, event: DomainEvent) -> None:
        """Forward the event to the registered listener."""

        if not self._running or self._listener is None:
            raise RuntimeError("EventPublisher is not running")
        await self._listener(event)

    async def start(self, listener: EventListener) -> None:
        """Activate the publisher with the given listener callback."""

        self._listener = listener
        self._running = True

    async def stop(self) -> None:
        """Deactivate the publisher and drop the listener reference."""

        self._listener = None
        self._running = False

    async def emit(self, event: DomainEvent) -> None:
        """Helper used in tests to simulate inbound events."""

        await self.publish(event)

    @property
    def is_running(self) -> bool:
        return self._running


__all__ = ["EventPublisher", "EventListener"]
