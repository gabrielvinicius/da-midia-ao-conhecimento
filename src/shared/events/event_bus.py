"""In-memory event bus implementation for the application."""
from __future__ import annotations

from typing import Optional

from .domain_events import DomainEvent
from .event_publisher import EventPublisher
from .subscription_manager import EventHandler, EventKey, SubscriptionManager


class EventBus:
    """Coordinates domain event subscriptions and dispatching."""

    def __init__(
        self,
        publisher: Optional[EventPublisher] = None,
        subscription_manager: Optional[SubscriptionManager] = None,
    ) -> None:
        self._publisher = publisher or EventPublisher()
        self._subscriptions = subscription_manager or SubscriptionManager()
        self._is_listening = False

    def subscribe(self, event: EventKey, handler: EventHandler) -> None:
        """Register ``handler`` for ``event``."""

        self._subscriptions.add_subscription(event, handler)

    def unsubscribe(self, event: EventKey, handler: EventHandler) -> None:
        """Remove ``handler`` from the subscriber list for ``event``."""

        self._subscriptions.remove_subscription(event, handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish ``event`` to the broker and local subscribers."""

        await self._publisher.publish(event)
        await self._dispatch(event)

    async def start_listener(self) -> None:
        """Begin consuming events from the underlying publisher."""

        if self._is_listening:
            return

        await self._publisher.start(self._handle_incoming_event)
        self._is_listening = True

    async def stop_listener(self) -> None:
        """Stop consuming events from the underlying publisher."""

        if not self._is_listening:
            return

        await self._publisher.stop()
        self._is_listening = False

    async def _handle_incoming_event(self, event: DomainEvent) -> None:
        await self._dispatch(event)

    async def _dispatch(self, event: DomainEvent) -> None:
        handlers = self._subscriptions.get_handlers(type(event))
        if not handlers and getattr(event, "event_name", None):
            handlers = self._subscriptions.get_handlers(event.event_name)
        if not handlers:
            return

        for handler in handlers:
            await handler(event)

    def has_subscribers(self, event: EventKey) -> bool:
        return self._subscriptions.has_subscribers(event)

    def clear(self) -> None:
        self._subscriptions.clear()

    @property
    def is_listening(self) -> bool:
        """Return ``True`` when the listener has been started."""

        return self._is_listening


__all__ = ["EventBus"]
