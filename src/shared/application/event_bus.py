"""Contrato do barramento de eventos usado pela camada de aplicação."""
from __future__ import annotations

from typing import Awaitable, Callable, Iterable, Protocol, Type, TypeVar

from src.shared.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]
TEvent = TypeVar("TEvent", bound=DomainEvent)


class SupportsEventBus(Protocol):
    """Protocol defining the contract expected from an event bus implementation."""

    async def publish(self, event: DomainEvent) -> None: ...

    async def publish_many(self, events: Iterable[DomainEvent]) -> None: ...

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None: ...

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None: ...

    async def start_listener(self) -> None: ...

    async def stop_listener(self) -> None: ...


__all__ = ["EventHandler", "SupportsEventBus", "TEvent"]
