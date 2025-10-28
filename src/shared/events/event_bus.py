"""Event bus orchestration and factory helpers.

The :class:`EventBus` coordinates domain events and delegates broker
interactions to an implementation that respects
``BrokerPublisher``.  The module also exposes :func:`get_event_bus`, a
factory capable of instantiating different publisher backends and
subscription strategies based on configuration.
"""
from __future__ import annotations

from typing import Dict, Optional

from .async_queue_publisher import AsyncQueueBrokerPublisher
from .domain_events import DomainEvent
from .event_publisher import EventPublisher
from .interfaces import (
    BrokerPublisher,
    EventBusConfig,
    EventHandler,
    EventKey,
    SubscriptionStrategy,
)
from .subscription_manager import SubscriptionManager


class EventBus:
    """Coordinates domain event subscriptions and dispatching."""

    def __init__(
        self,
        publisher: Optional[BrokerPublisher] = None,
        subscription_manager: Optional[SubscriptionStrategy] = None,
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


_EVENT_BUS_CACHE: Dict[tuple, EventBus] = {}


def _create_publisher(config: EventBusConfig) -> BrokerPublisher:
    backend = config.publisher_backend.lower()
    options = dict(config.publisher_options)
    if backend in {"inmemory", "memory", "default"}:
        return EventPublisher()
    if backend in {"async_queue", "queue"}:
        return AsyncQueueBrokerPublisher(**options)
    raise ValueError(f"Unsupported publisher backend: {config.publisher_backend!r}")


def _create_subscription_strategy(config: EventBusConfig) -> SubscriptionStrategy:
    strategy = config.subscription_strategy.lower()
    if strategy in {"default", "inmemory"}:
        return SubscriptionManager()
    raise ValueError(f"Unsupported subscription strategy: {config.subscription_strategy!r}")


def get_event_bus(config: Optional[EventBusConfig] = None, *, force_new: bool = False) -> EventBus:
    """Return a configured :class:`EventBus` instance.

    Parameters
    ----------
    config:
        Optional :class:`EventBusConfig` controlling which publisher and
        subscription strategy should be used.  When omitted the
        in-memory implementations are selected.
    force_new:
        When ``True`` a fresh instance is created regardless of whether a
        cached instance already exists for the provided configuration.
    """

    effective_config = config or EventBusConfig()
    cache_key = effective_config.cache_key()
    if force_new or cache_key not in _EVENT_BUS_CACHE:
        publisher = _create_publisher(effective_config)
        subscriptions = _create_subscription_strategy(effective_config)
        _EVENT_BUS_CACHE[cache_key] = EventBus(
            publisher=publisher,
            subscription_manager=subscriptions,
        )
    return _EVENT_BUS_CACHE[cache_key]


__all__ = ["EventBus", "EventBusConfig", "get_event_bus"]
