# src/shared/events/event_bus.py
from typing import Callable, Coroutine, Dict, Union, Type, Optional
import asyncio
import logging

from src.shared.events.domain_events import DomainEvent
from src.shared.events.event_bus_config import redis_client, celery_app as celery
from src.shared.events.event_publisher import EventPublisher
from src.shared.events.event_listener import EventListener
from src.shared.events.subscription_manager import EventSubscriptionManager

logger = logging.getLogger(__name__)


class EventBus:
    """
    A facade for the event system, coordinating publishing, subscribing,
    and listening for domain events.
    """
    def __init__(
        self,
        publisher: EventPublisher,
        subscription_manager: EventSubscriptionManager,
        listener: EventListener,
    ):
        self.publisher = publisher
        self.subscription_manager = subscription_manager
        self.listener = listener

    def subscribe(self, event_type: Union[str, Type[DomainEvent]], handler: Callable[[Dict], Union[None, Coroutine]]):
        """Registers a local handler for a domain event type."""
        self.subscription_manager.subscribe(event_type, handler)

    async def publish(self, event: DomainEvent):
        """Publishes a domain event."""
        await self.publisher.publish(event)

    def start_listener(self):
        """Starts the event listener."""
        self.listener.start()

    async def stop_listener(self):
        """Stops the event listener and closes connections."""
        self.listener.stop()
        try:
            await self.publisher.redis_client.close()
            logger.info("[EventBus] Redis client closed.")
        except Exception as e:
            logger.error(f"[EventBus] Failed to close Redis: {e}")


# --- Singleton Instance ---
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Initializes and returns a singleton instance of the EventBus.
    This function wires together all the components of the event system.
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        # 1. Initialize components
        subscription_manager = EventSubscriptionManager()
        publisher = EventPublisher(redis_client)
        listener = EventListener(redis_client, subscription_manager)

        # 2. Create EventBus facade
        _event_bus_instance = EventBus(
            publisher=publisher,
            subscription_manager=subscription_manager,
            listener=listener
        )
    return _event_bus_instance