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
