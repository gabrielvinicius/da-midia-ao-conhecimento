"""Factory do event bus da aplicação.

Decisão arquitetural: o event bus é **apenas in-process** (memory).
Integração entre processos (API ↔ worker) deve ocorrer via Celery/DB, não via bus.
"""

from __future__ import annotations

from src.shared.infrastructure.messaging.event_bus import (
    SupportsEventBus,
    create_inmemory_event_bus,
)


def get_event_bus() -> SupportsEventBus:
    """Retorna um event bus in-memory (in-process)."""
    return create_inmemory_event_bus()


__all__ = ["get_event_bus"]
