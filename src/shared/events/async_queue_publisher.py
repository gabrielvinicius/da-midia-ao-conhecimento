"""Asynchronous queue based publisher used to decouple event dispatch."""
from __future__ import annotations

import asyncio
from typing import Optional

from src.shared.events.domain_events import DomainEvent
from src.shared.events.event_publisher import EventListener


class AsyncQueueBrokerPublisher:
    """Publishes events via an internal asyncio.Queue processed by a worker task."""

    def __init__(self, *, queue_maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=queue_maxsize)
        self._listener: Optional[EventListener] = None
        self._worker: Optional[asyncio.Task[None]] = None
        self._running: bool = False

    async def publish(self, event: DomainEvent) -> None:
        """Enqueue an event to be processed by the background worker."""

        if not self._running:
            raise RuntimeError("AsyncQueueBrokerPublisher is not running")
        await self._queue.put(event)

    async def start(self, listener: EventListener) -> None:
        """Start processing events by launching a background consumer task."""

        if self._running:
            return

        self._listener = listener
        self._running = True
        self._worker = asyncio.create_task(self._consume(), name="event-bus-consumer")

    async def stop(self) -> None:
        """Stop the background worker gracefully."""

        if not self._running:
            return

        self._running = False
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:  # pragma: no cover - expected path
                pass
        self._worker = None
        self._listener = None

        # Drain remaining events to avoid leaking references
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()

    async def emit(self, event: DomainEvent) -> None:
        """Directly dispatch an event to the listener (used in tests)."""

        if self._listener is None:
            raise RuntimeError("Listener not registered")
        await self._listener(event)

    @property
    def is_running(self) -> bool:
        return self._running

    async def _consume(self) -> None:
        """Consume events from the queue and forward them to the listener."""

        assert self._listener is not None, "Listener must be set before starting"
        listener = self._listener

        try:
            while True:
                event = await self._queue.get()
                try:
                    await listener(event)
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            pass


__all__ = ["AsyncQueueBrokerPublisher"]
