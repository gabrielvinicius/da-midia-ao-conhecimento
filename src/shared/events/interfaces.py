"""Structural contracts for the shared event system components.

This module centralises the common protocol definitions used by the
event bus.  By relying on protocols instead of concrete classes we can
plug different publisher backends or subscription strategies without
modifying the core orchestration logic.
"""

from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    Callable,
    Protocol,
    Sequence,
    Type,
    Union,
    runtime_checkable,
)

from .domain_events import DomainEvent

IncomingEventHandler = Callable[[DomainEvent], Awaitable[None]]
EventHandler = IncomingEventHandler
EventKey = Union[str, Type[DomainEvent]]


@runtime_checkable
class BrokerPublisher(Protocol):
    """Minimal contract required from an external event publisher."""

    async def publish(self, event: DomainEvent) -> None:
        """Send ``event`` to the underlying broker."""

    async def start(self, on_event: IncomingEventHandler) -> None:
        """Begin consuming messages and invoke ``on_event`` for each payload."""

    async def stop(self) -> None:
        """Stop consuming messages from the broker."""

    @property
    def is_running(self) -> bool:
        """Return ``True`` when the publisher is actively listening."""


@runtime_checkable
class SubscriptionStrategy(Protocol):
    """Strategy contract for managing event subscriptions."""

    def add_subscription(self, event: EventKey, handler: EventHandler) -> None:
        """Register ``handler`` for ``event``."""

    def remove_subscription(self, event: EventKey, handler: EventHandler) -> None:
        """Remove ``handler`` from the subscriber list for ``event``."""

    def get_handlers(self, event: EventKey) -> Sequence[EventHandler]:
        """Return the handlers registered for ``event``."""

    def has_subscribers(self, event: EventKey) -> bool:
        """Return ``True`` when ``event`` has at least one handler."""

    def clear(self) -> None:
        """Remove all registered subscriptions."""
__all__ = [
    "BrokerPublisher",
    "SubscriptionStrategy",
    "IncomingEventHandler",
    "EventHandler",
    "EventKey",
]

