# src/shared/events/event_listener.py
import asyncio
import json
import logging
from typing import Optional
import redis.asyncio as aioredis

from src.shared.events.subscription_manager import EventSubscriptionManager

logger = logging.getLogger(__name__)


class EventListener:
    """
    Listens for events from the message broker and dispatches them to registered handlers.
    """
    def __init__(self, redis_client: aioredis.Redis, subscription_manager: EventSubscriptionManager):
        self.redis_client = redis_client
        self.subscription_manager = subscription_manager
        self._listener_task: Optional[asyncio.Task] = None

    async def _listen(self):
        """
        The main loop that listens for messages from Redis and dispatches them.
        """
        while True:
            try:
                pubsub = self.redis_client.pubsub()
                subscribers = self.subscription_manager.subscribers
                if not subscribers:
                    await asyncio.sleep(1)  # Avoid busy-looping
                    continue

                await pubsub.subscribe(*subscribers.keys())

                async for message in pubsub.listen():
                    if message["type"] == "message":
                        event_type = message["channel"]
                        if isinstance(event_type, bytes):
                            event_type = event_type.decode()

                        data = json.loads(message["data"])
                        handlers = self.subscription_manager.get_handlers(event_type)
                        for handler in handlers:
                            if asyncio.iscoroutinefunction(handler):
                                asyncio.create_task(handler(data))
                            else:
                                handler(data)
            except Exception as e:
                logger.warning(f"[EventListener] Redis error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

    def start(self):
        """Starts the event listener task in the background."""
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("[EventListener] Listener started.")

    def stop(self):
        """Stops the event listener task."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            logger.info("[EventListener] Listener stopped.")
