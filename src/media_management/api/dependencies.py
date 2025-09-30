# src/media_management/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.media_management.application.media_service import MediaService
from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import StorageServiceFactory

# --- Service and Query Getters ---

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_media_service(container: Annotated[dict, Depends(get_container)]) -> MediaService:
    return container["media_service"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]

def get_storage_service_factory(container: Annotated[dict, Depends(get_container)]) -> StorageServiceFactory:
    return container["storage_service_factory"]
