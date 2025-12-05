# src/transcription/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)


class TranscriptionDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionDependencies:
    service: TranscriptionService


def get_transcription_dependencies() -> TranscriptionDependencies:
    raise TranscriptionDependenciesNotConfigured(
        "Transcription dependencies are not configured. Register providers in the lifespan handler."
    )


TranscriptionDeps = Annotated[
    TranscriptionDependencies, Depends(get_transcription_dependencies)
]


def get_transcription_service(deps: TranscriptionDeps) -> TranscriptionService:
    """Get transcription service dependency."""
    return deps.service


__all__ = [
    "TranscriptionDependencies",
    "TranscriptionDependenciesNotConfigured",
    "get_transcription_dependencies",
    "get_transcription_service",
]