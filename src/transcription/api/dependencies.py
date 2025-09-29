# src/transcription/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.media_management.application.queries.media_queries import MediaQueries

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_transcription_queries(container: Annotated[dict, Depends(get_container)]) -> TranscriptionQueries:
    return container["transcription_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]
