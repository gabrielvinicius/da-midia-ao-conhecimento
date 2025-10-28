"""Helpers that encapsulate application lifecycle orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.shared.events.event_bus import EventBus


class CacheClient(Protocol):
    """Minimal cache protocol used during application bootstrap."""

    async def connect(self) -> None:  # pragma: no cover - protocol definition
        ...

    async def disconnect(self) -> None:  # pragma: no cover - protocol definition
        ...


@dataclass
class ApplicationResources:
    """Infrastructure resources that require explicit lifecycle management."""

    event_bus: EventBus
    cache: CacheClient


async def start_application_resources(resources: ApplicationResources) -> None:
    """Initialize long-lived infrastructure resources."""

    await resources.event_bus.start_listener()
    await resources.cache.connect()


async def stop_application_resources(resources: ApplicationResources) -> None:
    """Gracefully release infrastructure resources."""

    await resources.cache.disconnect()
    await resources.event_bus.stop_listener()


__all__ = [
    "ApplicationResources",
    "start_application_resources",
    "stop_application_resources",
]
