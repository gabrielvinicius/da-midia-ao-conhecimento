# src/transcription/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_transcription_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["transcription_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_queries"]

def get_set_speaker_aliases_handler(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["set_speaker_aliases_handler"]
