"""O barramento de eventos de cada processo de worker.

Cada processo do Celery tem um único barramento em memória, no qual a
montagem do worker registra as reações aos eventos (MediaWorkerApp). As
tarefas de todos os módulos publicam nele; um barramento novo por tarefa não
teria ninguém inscrito. É o único estado global de mensageria, e fica aqui,
explícito, em vez de espalhado pelas tarefas.
"""
from __future__ import annotations

from typing import Optional

from src.shared.application.event_bus import SupportsEventBus
from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus

_PROCESS_BUS: Optional[SupportsEventBus] = None


def process_event_bus() -> SupportsEventBus:
    global _PROCESS_BUS
    if _PROCESS_BUS is None:
        _PROCESS_BUS = get_event_bus()
    return _PROCESS_BUS


def reset_process_event_bus() -> None:
    """Usado após o fork do worker e nos testes."""
    global _PROCESS_BUS
    _PROCESS_BUS = None


__all__ = ["process_event_bus", "reset_process_event_bus"]
