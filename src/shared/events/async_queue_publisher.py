"""Async queue based publisher adapter.

The adapter emulates the behaviour of an external broker using an
``asyncio.Queue``.  It is lightweight enough to be used in tests or
development environments while still exercising the asynchronous
publish/consume workflow expected from real streaming services.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .domain_events import DomainEvent
from .event_publisher import EventPublisher
from .interfaces import IncomingEventHandler


class AsyncQueueBrokerPublisher(EventPublisher):
    """Concrete publisher backed by :class:`asyncio.Queue`."""

    def __init__(self, queue: Optional[asyncio.Queue[DomainEvent]] = None) -> None:
        super().__init__()
        self._queue: asyncio.Queue[DomainEvent] = queue or asyncio.Queue()
        self._consumer_task: Optional[asyncio.Task[None]] = None

    async def publish(self, event: DomainEvent) -> None:
        await self._queue.put(event)
        if self.is_running:
            await self._ensure_consumer()

    async def start(self, on_event: IncomingEventHandler) -> None:
        await super().start(on_event)
        await self._ensure_consumer()

    async def stop(self) -> None:
        await super().stop()
        if self._consumer_task is None:
            return
        self._consumer_task.cancel()
        try:
            await self._consumer_task
        except asyncio.CancelledError:  # pragma: no cover - expected cancellation path
            pass
        finally:
            self._consumer_task = None

    async def _ensure_consumer(self) -> None:
        if not self.is_running:
            return
        if self._consumer_task and not self._consumer_task.done():
            return
        loop = asyncio.get_running_loop()
        self._consumer_task = loop.create_task(self._consume())

    async def _consume(self) -> None:
        while self.is_running:
            event = await self._queue.get()
            try:
                await self.emit(event)
            finally:
                self._queue.task_done()


__all__ = ["AsyncQueueBrokerPublisher"]

