"""High-level event bus orchestration."""
from __future__ import annotations

from typing import Iterable, Optional, Type

from src.shared.events.async_queue_publisher import AsyncQueueBrokerPublisher
from src.shared.events.domain_events import DomainEvent
from src.shared.events.subscription_manager import EventHandler, SubscriptionManager


class EventBus:
    """Coordinates event publishing and subscription management."""

    def __init__(
        self,
        *,
        publisher,
        subscription_manager: Optional[SubscriptionManager] = None,
    ) -> None:
        self._publisher = publisher
        self._subscriptions = subscription_manager or SubscriptionManager()
        self._is_listening: bool = False

    # --------------------------------------------------------------------- #
    # Subscription handling
    # --------------------------------------------------------------------- #
    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._subscriptions.subscribe(event_type, handler)

    def unsubscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._subscriptions.unsubscribe(event_type, handler)

    # --------------------------------------------------------------------- #
    # Publishing operations
    # --------------------------------------------------------------------- #
    async def publish(self, event: DomainEvent) -> None:
        if self._is_listening:
            await self._publisher.publish(event)
            return
        await self._dispatch(event)

    async def publish_many(self, events: Iterable[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    # --------------------------------------------------------------------- #
    # Listener lifecycle
    # --------------------------------------------------------------------- #
    @property
    def is_listening(self) -> bool:
        return self._is_listening

    async def start_listener(self) -> None:
        if self._is_listening:
            return

        async def _listener(event: DomainEvent) -> None:
            await self._dispatch(event)

        await self._publisher.start(_listener)
        self._is_listening = True

    async def stop_listener(self) -> None:
        if not self._is_listening:
            return

        await self._publisher.stop()
        self._subscriptions.clear()
        self._is_listening = False

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    async def _dispatch(self, event: DomainEvent) -> None:
        handlers = self._subscriptions.handlers_for(type(event))
        for handler in handlers:
            await handler(event)


def create_inmemory_event_bus() -> EventBus:
    """Factory that returns a fully wired in-memory event bus instance."""

    return EventBus(
        publisher=AsyncQueueBrokerPublisher(),
        subscription_manager=SubscriptionManager(),
    )


__all__ = [
    "EventBus",
    "create_inmemory_event_bus",
    "SubscriptionManager",
]
