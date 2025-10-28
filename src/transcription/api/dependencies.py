# src/transcription/api/dependencies.py
from typing import Annotated
from fastapi import Depends, Request

from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.transcription_service import TranscriptionService
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.application.queries import TranscriptionQueries
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    """Return the modules registry stored in the application state."""
    return request.app.state.modules


def get_transcription_service(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> TranscriptionService:
    """Get transcription service dependency."""
    return modules.transcription.service


def get_transcription_repository(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> TranscriptionRepository:
    return modules.transcription.repository


def get_transcription_queries(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> TranscriptionQueries:
    return modules.transcription.queries


def get_media_queries(
    modules: Annotated[ModulesRegistry, Depends(get_modules)]
) -> MediaQueries:
    return modules.media_management.queries
