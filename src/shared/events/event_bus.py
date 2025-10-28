"""In-memory event bus implementation for the application."""
from __future__ import annotations

from typing import Optional

from .domain_events import DomainEvent
from .event_publisher import EventHandler, EventPublisher
from .subscription_manager import EventKey, SubscriptionManager


class EventBus:
    """Simple event bus coordinating subscriptions and publications."""

    def __init__(
        self,
        publisher: Optional[EventPublisher] = None,
        subscription_manager: Optional[SubscriptionManager] = None,
    ) -> None:
        self._publisher = publisher or EventPublisher()
        self._subscriptions = subscription_manager or SubscriptionManager()

    def subscribe(self, event: EventKey, handler: EventHandler) -> None:
        self._subscriptions.add_subscription(event, handler)

    def unsubscribe(self, event: EventKey, handler: EventHandler) -> None:
        self._subscriptions.remove_subscription(event, handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._subscriptions.get_handlers(type(event))
        if not handlers and event.name:
            handlers = self._subscriptions.get_handlers(event.name)
        if handlers:
            await self._publisher.publish(event, handlers)

    def has_subscribers(self, event: EventKey) -> bool:
        return self._subscriptions.has_subscribers(event)

    def clear(self) -> None:
        self._subscriptions.clear()


__all__ = ["EventBus"]
