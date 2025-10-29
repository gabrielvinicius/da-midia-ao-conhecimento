from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Callable, Dict, List, Type

class Event(ABC):
    """Base class for all domain events."""
    pass

class EventHandler(ABC):
    """Base class for all event handlers."""
    @abstractmethod
    async def handle(self, event: Event):
        """Handles a specific event."""
        pass

class EventBus(ABC):
    """Abstract base class for an Event Bus."""
    @abstractmethod
    def subscribe(self, event_type: Type[Event], handler: EventHandler):
        """Subscribes a handler to a specific event type."""
        pass

    @abstractmethod
    async def publish(self, event: Event):
        """Publishes an event to all subscribed handlers."""
        pass

class InMemoryEventBus(EventBus):
    """An in-memory implementation of an Event Bus."""
    def __init__(self):
        self._handlers: Dict[Type[Event], List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: Type[Event], handler: EventHandler):
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event):
        event_type = type(event)
        for handler in self._handlers[event_type]:
            await handler.handle(event)
