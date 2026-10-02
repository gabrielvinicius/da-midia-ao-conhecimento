"""Event bus implementation and related components."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import (
    Awaitable,
    Callable,
    DefaultDict,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
)

from src.shared.application.event_bus import SupportsEventBus  # noqa: F401 (reexportado)
from src.shared.domain.events import DomainEvent

logger = logging.getLogger(__name__)

# --- From subscription_manager.py ---
EventHandler = Callable[[DomainEvent], Awaitable[None]]
TEvent = TypeVar("TEvent", bound=DomainEvent)

class SubscriptionManager:
    """Keeps track of event handlers registered for each event type."""

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[
            Type[DomainEvent],
            List[EventHandler],
        ] = defaultdict(list)

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Register an asynchronous handler for a given event type."""
        handlers = self._subscriptions[event_type]
        if handler not in handlers:
            handlers.append(handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return

        try:
            handlers.remove(handler)
        except ValueError:  # pragma: no cover - defensive guard
            pass

        if not handlers:
            self._subscriptions.pop(event_type, None)

    def handlers_for(self, event_type: Type[TEvent]) -> Iterable[EventHandler]:
        """Return handlers for the provided event type."""
        return tuple(self._subscriptions.get(event_type, ()))

    def clear(self) -> None:
        """Remove all registered handlers (used when stopping the bus)."""
        self._subscriptions.clear()

# --- From event_publisher.py ---
EventListener = Callable[[DomainEvent], Awaitable[None]]

# --- From async_queue_publisher.py ---
class AsyncQueueBrokerPublisher:
    """Publishes events via an internal asyncio.Queue processed by a worker task."""

    def __init__(self, *, queue_maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=queue_maxsize)
        self._listener: Optional[EventListener] = None
        self._worker: Optional[asyncio.Task[None]] = None
        self._running: bool = False

    async def publish(self, event: DomainEvent) -> None:
        """Enqueue an event to be processed by the background worker."""
        if not self._running:
            raise RuntimeError(
                "AsyncQueueBrokerPublisher não está em execução. "
                "Chame start(listener) antes de publicar eventos."
            )
        await self._queue.put(event)

    async def start(self, listener: EventListener) -> None:
        """Start processing events by launching a background consumer task."""
        if self._running:
            return

        self._listener = listener
        self._running = True
        self._worker = asyncio.create_task(self._consume(), name="event-bus-consumer")

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self._running:
            return

        self._running = False
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:  # pragma: no cover - expected path
                pass
        self._worker = None
        self._listener = None

        # Drain remaining events to avoid leaking references
        while not self._queue.empty():
            self._queue.get_nowait()
            self._queue.task_done()

    async def emit(self, event: DomainEvent) -> None:
        """Directly dispatch an event to the listener (used in tests)."""
        if self._listener is None:
            raise RuntimeError(
                f"Listener não registrado para {type(event).__name__}. "
                "Registre handlers antes de emitir eventos."
            )
        await self._listener(event)

    @property
    def is_running(self) -> bool:
        return self._running

    async def _consume(self) -> None:
        """Consume events from the queue and forward them to the listener."""
        assert self._listener is not None, "Listener must be set before starting"
        listener = self._listener

        try:
            while True:
                event = await self._queue.get()
                try:
                    await listener(event)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Uma falha ao tratar um evento não pode parar o consumidor:
                    # os eventos seguintes ainda precisam ser entregues.
                    logger.exception(
                        "Falha ao tratar o evento %s", type(event).__name__
                    )
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            pass

class InMemoryEventBus:
    """Barramento síncrono simples, usado em testes."""

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[
            Type[DomainEvent],
            List[EventHandler],
        ] = defaultdict(list)
        self._started: bool = False

    async def publish(self, event: DomainEvent) -> None:
        """Deliver an event to every registered handler."""
        handlers = list(self._subscriptions.get(type(event), []))
        for handler in handlers:
            await handler(event)

    async def publish_many(self, events: Iterable[DomainEvent]) -> None:
        """Publish a batch of events preserving order."""
        for event in events:
            await self.publish(event)

    def subscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Register an asynchronous handler for the given event."""
        self._subscriptions[event_type].append(handler)

    def unsubscribe(self, event_type: Type[TEvent], handler: EventHandler) -> None:
        """Unregister an event handler."""
        handlers = self._subscriptions.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:  # pragma: no cover - defensive guard
            pass

        if not handlers:
            self._subscriptions.pop(event_type, None)

    def has_subscribers(self, event_type: Type[DomainEvent]) -> bool:
        """Utility used in smoke tests to confirm registration."""
        return bool(self._subscriptions.get(event_type))

    async def start_listener(self) -> None:
        """Hook invoked during application startup to activate the bus."""
        self._started = True

    async def stop_listener(self) -> None:
        """Hook invoked during shutdown to flush subscriptions."""
        self._subscriptions.clear()
        self._started = False

# --- From event_bus.py (top-level) ---
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
        failures: list[BaseException] = []
        for handler in handlers:
            # Cada handler é isolado: a falha de um módulo não impede os demais
            # de reagirem ao mesmo evento.
            try:
                await handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception(
                    "Handler %s falhou ao tratar %s",
                    getattr(handler, "__qualname__", repr(handler)),
                    type(event).__name__,
                )
                failures.append(exc)
        if failures and not self._is_listening:
            # Na entrega síncrona (workers), quem publicou precisa saber da falha.
            raise failures[0]


def create_inmemory_event_bus() -> EventBus:
    """Factory that returns a fully wired in-memory event bus instance."""
    return EventBus(
        publisher=AsyncQueueBrokerPublisher(),
        subscription_manager=SubscriptionManager(),
    )

__all__ = [
    "EventListener",
    "AsyncQueueBrokerPublisher",
    "EventHandler",
    "SubscriptionManager",
    "SupportsEventBus",
    "InMemoryEventBus",
    "EventBus",
    "create_inmemory_event_bus",
]
