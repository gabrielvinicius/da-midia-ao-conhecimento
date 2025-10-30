# src/transcription/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.media_management.api.dependencies import get_media_queries
from src.media_processing.transcription.application.transcription_service import TranscriptionService
from src.media_processing.transcription.application.queries import TranscriptionQueries


class TranscriptionDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionDependencies:
    service: TranscriptionService
    queries: TranscriptionQueries


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


def get_transcription_queries(deps: TranscriptionDeps) -> TranscriptionQueries:
    return deps.queries


__all__ = [
    "TranscriptionDependencies",
    "TranscriptionDependenciesNotConfigured",
    "get_transcription_dependencies",
    "get_transcription_queries",
    "get_transcription_service",
    "get_media_queries",
]
