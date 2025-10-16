# src/media_management/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_media_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_service"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_queries"]

def get_media_settings(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_settings"]
