"""Factory for creating the application event bus.

Currently supports in-memory bus, with room for future backends
(e.g., Redis/Kafka) driven by environment variables.
"""

from __future__ import annotations

import os
from typing import Optional

from src.shared.infrastructure.messaging.event_bus import (
    SupportsEventBus,
    create_inmemory_event_bus,
)


def get_event_bus(backend: Optional[str] = None) -> SupportsEventBus:
    backend = (backend or os.getenv("EVENT_BUS", "memory")).lower()
    if backend == "memory":
        # Coordinated EventBus (queue + subscription manager) keeps contexts consistent
        return create_inmemory_event_bus()
    raise ValueError(f"Unsupported EVENT_BUS backend: {backend}")


__all__ = ["get_event_bus"]
