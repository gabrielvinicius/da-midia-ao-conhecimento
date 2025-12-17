from __future__ import annotations

from typing import Optional

from .event_bus import SupportsEventBus
from .event_bus_factory import get_event_bus

_cached_bus: SupportsEventBus | None = None


def set_event_bus(bus: SupportsEventBus) -> None:
    """Inject a pre-configured event bus shared across contexts."""
    global _cached_bus
    _cached_bus = bus


def resolve_event_bus(existing: Optional[SupportsEventBus] = None) -> SupportsEventBus:
    """Return provided bus, cached bus, or create default in-memory bus."""
    if existing is not None:
        return existing
    global _cached_bus
    if _cached_bus is None:
        _cached_bus = get_event_bus()
    return _cached_bus


__all__ = ["resolve_event_bus", "set_event_bus"]
