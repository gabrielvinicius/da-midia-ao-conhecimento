from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.infrastructure.dependencies.builders import (
    build_transcription_service,
)
from src.shared.infrastructure.database.db import get_db


class TranscriptionDependenciesNotConfiguredError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionDependencies:
    service: TranscriptionService


def _get_event_bus(request: Request):
    bus = getattr(request.app.state, "event_bus", None)
    return bus


def get_transcription_dependencies(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TranscriptionDependencies:
    """Serviço de transcrição da requisição, pela montagem única do módulo."""
    return TranscriptionDependencies(
        service=build_transcription_service(session, _get_event_bus(request))
    )


TranscriptionDeps = Annotated[
    TranscriptionDependencies, Depends(get_transcription_dependencies)
]


def get_transcription_service(deps: TranscriptionDeps) -> TranscriptionService:
    """Get transcription service dependency."""
    return deps.service


__all__ = [
    "TranscriptionDependencies",
    "TranscriptionDependenciesNotConfiguredError",
    "get_transcription_dependencies",
    "get_transcription_service",
]
