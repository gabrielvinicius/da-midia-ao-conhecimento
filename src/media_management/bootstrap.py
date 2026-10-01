"""Montagem do módulo de mídias para a API.

Os serviços vêm das fábricas únicas do módulo (infrastructure/dependencies/
builders.py), as mesmas usadas pelos workers. São montados uma vez, com a
sessão por requisição (RequestScopedSession), e entregues às rotas pelas
dependências.
"""
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from fastapi import FastAPI

from src.media_management.api.dependencies import get_media_read_service, get_media_service
from src.media_management.application.services.media_read_service import MediaReadService
from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.dependencies.builders import (
    build_media_read_service,
    build_media_service,
)
from src.shared.application.event_bus import SupportsEventBus


@dataclass
class MediaModule:
    """Public surface used by the media API and other modules."""

    media_service: MediaService
    media_read_service: MediaReadService


@dataclass
class MediaAdminContext:
    """Administrative operations that can be shared with other modules."""

    media_service: MediaService


def build_media_components(
    session: Any,
    *,
    storage_service_factory: Any,
    event_bus: Optional[SupportsEventBus] = None,
    **_unused: Any,
) -> Tuple[MediaModule, MediaAdminContext]:
    media_service = build_media_service(
        session=session, storage_factory=storage_service_factory, event_bus=event_bus
    )
    module = MediaModule(
        media_service=media_service,
        media_read_service=build_media_read_service(session),
    )
    return module, MediaAdminContext(media_service=media_service)


def bind_media_module(app: FastAPI, module: MediaModule) -> None:
    """Register dependency overrides for media use cases."""
    app.dependency_overrides[get_media_service] = lambda: module.media_service
    app.dependency_overrides[get_media_read_service] = lambda: module.media_read_service


__all__ = [
    "MediaModule",
    "MediaAdminContext",
    "bind_media_module",
    "build_media_components",
]
