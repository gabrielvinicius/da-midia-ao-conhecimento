"""Montagem do módulo de mídias nos workers: assina os eventos que mudam o
estado da mídia.

Fica na raiz do módulo (camada de montagem) porque abre a sessão do banco.
Antes, essas inscrições estavam no worker do processamento, que precisava
conhecer o módulo de mídias; agora cada módulo assina o que lhe interessa,
como o de avisos.
"""
from __future__ import annotations

from typing import Awaitable, Callable

import structlog

from src.media_management.application.event_handlers import MediaEventHandlers
from src.media_management.infrastructure.dependencies.builders import build_media_event_handlers
from src.shared.application.event_bus import SupportsEventBus
from src.shared.domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    DomainEvent,
    MediaProcessingFailed,
    MediaProcessingStarted,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)

Reaction = Callable[[MediaEventHandlers, DomainEvent], Awaitable[None]]

# Evento → reação. Um novo evento que mude o estado da mídia entra aqui.
MEDIA_REACTIONS: dict[type[DomainEvent], Reaction] = {
    MediaProcessingStarted: MediaEventHandlers.handle_media_processing_started,
    TranscriptionCompleted: MediaEventHandlers.handle_transcription_completed,
    TranscriptionFailed: MediaEventHandlers.handle_transcription_failed,
    MediaProcessingFailed: MediaEventHandlers.handle_media_processing_failed,
    AnalysisCompleted: MediaEventHandlers.handle_analysis_completed,
    AnalysisFailed: MediaEventHandlers.handle_analysis_failed,
}


def _subscriber(event_bus: SupportsEventBus, reaction: Reaction) -> Callable[[DomainEvent], Awaitable[None]]:
    async def handle(event: DomainEvent) -> None:
        async with AsyncSessionLocal() as session:
            handlers = build_media_event_handlers(
                session=session, storage_factory=StorageServiceFactory(), event_bus=event_bus
            )
            await reaction(handlers, event)

    return handle


def bind_media_subscribers(event_bus: SupportsEventBus) -> None:
    for event_type, reaction in MEDIA_REACTIONS.items():
        event_bus.subscribe(event_type, _subscriber(event_bus, reaction))


__all__ = ["MEDIA_REACTIONS", "bind_media_subscribers"]
