# src/transcription/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)


class TranscriptionDependenciesNotConfiguredError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionDependencies:
    service: TranscriptionService


def get_transcription_dependencies() -> TranscriptionDependencies:
    raise TranscriptionDependenciesNotConfiguredError(
        "Transcription dependencies are not configured. "
        "Register providers in the lifespan handler."
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
