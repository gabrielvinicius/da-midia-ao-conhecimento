# src/video_management/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated
from functools import lru_cache

from src.video_management.application.video_service import VideoService
from src.video_management.application.queries.video_queries import VideoQueries
from src.video_management.config.settings import VideoSettings

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_video_service(container: Annotated[dict, Depends(get_container)]) -> VideoService:
    return container["video_service"]

def get_video_queries(container: Annotated[dict, Depends(get_container)]) -> VideoQueries:
    return container["video_queries"]

# --- Settings Getter ---

@lru_cache()
def get_video_settings() -> VideoSettings:
    return VideoSettings()
