"""Structural contracts for the shared event system components.

This module centralises the common protocol definitions used by the
event bus.  By relying on protocols instead of concrete classes we can
plug different publisher backends or subscription strategies without
modifying the core orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Mapping,
    Protocol,
    Sequence,
    Tuple,
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


def _as_tuple(mapping: Mapping[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    """Normalise mapping data structures for hashing or comparisons."""

    return tuple(sorted(mapping.items(), key=lambda item: item[0]))


@dataclass(frozen=True)
class EventBusConfig:
    """Configuration payload used by :func:`get_event_bus`."""

    publisher_backend: str = "inmemory"
    subscription_strategy: str = "default"
    publisher_options: Mapping[str, Any] = field(default_factory=dict)
    subscription_options: Mapping[str, Any] = field(default_factory=dict)

    def cache_key(self) -> Tuple[str, str, Tuple[Tuple[str, Any], ...], Tuple[Tuple[str, Any], ...]]:
        """Return a hashable representation of the configuration."""

        return (
            self.publisher_backend,
            self.subscription_strategy,
            _as_tuple(self.publisher_options),
            _as_tuple(self.subscription_options),
        )


__all__ = [
    "BrokerPublisher",
    "SubscriptionStrategy",
    "IncomingEventHandler",
    "EventHandler",
    "EventKey",
    "EventBusConfig",
]

