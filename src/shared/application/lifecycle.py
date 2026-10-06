"""Helpers that encapsulate application lifecycle orchestration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class EventBusClient(Protocol):
    """Lifecycle hooks expected from the application event bus."""

    async def start_listener(self) -> None:  # pragma: no cover - protocol definition
        ...

    async def stop_listener(self) -> None:  # pragma: no cover - protocol definition
        ...


@dataclass(slots=True)
class ApplicationResources:
    """Infra que requer gerenciamento explícito de ciclo de vida."""

    event_bus: EventBusClient


async def start_application_resources(resources: ApplicationResources) -> None:
    """Initialize long-lived infrastructure resources."""
    await resources.event_bus.start_listener()


async def stop_application_resources(resources: ApplicationResources) -> None:
    """Gracefully release infrastructure resources."""
    await resources.event_bus.stop_listener()


__all__ = [
    "ApplicationResources",
    "start_application_resources",
    "stop_application_resources",
]
