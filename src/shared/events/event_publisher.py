# src/shared/events/event_publisher.py
import json
import redis.asyncio as aioredis
from src.shared.events.domain_events import DomainEvent


class EventPublisher:
    """
    Responsible for publishing domain events to a message broker (Redis).
    """
    def __init__(self, redis_client: aioredis.Redis):
        self.redis_client = redis_client

    async def publish(self, event: DomainEvent):
        """
        Serializes and publishes a domain event to the appropriate Redis channel.
        """
        event_type = event.__class__.__name__
        try:
            data = event.to_dict()
            await self.redis_client.publish(event_type, json.dumps(data, default=str))
        except TypeError as e:
            raise ValueError(f"Error serializing event payload for {event_type}: {e}")
        except Exception as e:
            # Log and handle potential redis connection errors
            raise ConnectionError(f"Failed to publish event {event_type} to Redis: {e}") from e
