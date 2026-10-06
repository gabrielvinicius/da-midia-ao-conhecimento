"""O barramento de eventos de cada processo de worker.

Cada processo do Celery tem um único barramento em memória: as tarefas de
todos os módulos publicam nele, e as reações de cada módulo são inscritas
quando ele é criado. Um barramento novo por tarefa não teria ninguém
inscrito. É o único estado global de mensageria, e fica aqui, explícito.

As reações são informadas pela montagem do worker (celery_app), porque o
núcleo compartilhado não conhece os módulos. Uma falha ao inscrevê-las
sobe para a tarefa que pediu o barramento: antes, ela era registrada num
sinal do Celery, que a engole, e o worker seguia sem reagir a nada.
"""
from __future__ import annotations

from typing import Callable, Optional

from src.shared.application.event_bus import SupportsEventBus
from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus

Subscribe = Callable[[SupportsEventBus], None]

_PROCESS_BUS: Optional[SupportsEventBus] = None
_SUBSCRIBE: Optional[Subscribe] = None


def configure_process_subscribers(subscribe: Optional[Subscribe]) -> None:
    """Define as reações inscritas em cada barramento novo deste processo."""
    global _SUBSCRIBE
    _SUBSCRIBE = subscribe
    reset_process_event_bus()


def process_event_bus() -> SupportsEventBus:
    global _PROCESS_BUS
    if _PROCESS_BUS is None:
        bus = get_event_bus()
        if _SUBSCRIBE is not None:
            _SUBSCRIBE(bus)
        _PROCESS_BUS = bus
    return _PROCESS_BUS


def reset_process_event_bus() -> None:
    """Usado após o fork do worker e nos testes."""
    global _PROCESS_BUS
    _PROCESS_BUS = None


__all__ = ["configure_process_subscribers", "process_event_bus", "reset_process_event_bus"]
