# src/shared/events/subscription_manager.py
from typing import Dict, Callable, Coroutine, Union, Type, List
from src.shared.events.domain_events import DomainEvent


class EventSubscriptionManager:
    """
    Manages event subscriptions, mapping event types to their respective handlers.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Dict], Union[None, Coroutine]]]] = {}

    def subscribe(self, event_type: Union[str, Type[DomainEvent]], handler: Callable[[Dict], Union[None, Coroutine]]):
        """Registers a handler for a specific domain event type."""
        event_name = event_type if isinstance(event_type, str) else event_type.__name__
        
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)

    def get_handlers(self, event_type: str) -> List[Callable[[Dict], Union[None, Coroutine]]]:
        """Retrieves all handlers registered for a given event type."""
        return self.subscribers.get(event_type, [])
