"""Dependências da API de mídias.

Os serviços são montados uma única vez, por bootstrap.build_media_components
(com as fábricas de infrastructure/dependencies/builders.py), e ligados aqui
por bind_media_module. Sem essa ligação, as dependências falham em vez de
montar uma versão própria, diferente da usada pela aplicação.
"""
from fastapi import Request

from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.shared.application.event_bus import SupportsEventBus


def get_event_bus(request: Request) -> SupportsEventBus:
    """Retrieve the shared event bus from app state."""
    if not hasattr(request.app.state, "event_bus"):
        raise RuntimeError(
            "Event bus não inicializado no app.state. "
            "Verifique o bootstrap (main.lifespan) para injetar a instância."
        )
    return request.app.state.event_bus


def get_media_service() -> MediaService:
    raise NotImplementedError("MediaService não configurado (bind_media_module).")


def get_media_read_service() -> MediaReadService:
    raise NotImplementedError("MediaReadService não configurado (bind_media_module).")


__all__ = ["get_event_bus", "get_media_read_service", "get_media_service"]
