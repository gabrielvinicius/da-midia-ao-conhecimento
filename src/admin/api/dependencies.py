# src/admin/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries

# Helper to get the app container
def get_container(request: Request) -> dict:
    return request.app.state.container

# Dependency getters for the Admin module
def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]
