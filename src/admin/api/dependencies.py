# src/admin/api/dependencies.py
from fastapi import Request, Depends
from typing import Annotated

from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.admin.application.queries.admin_queries import AdminQueries

# Helper to get the app container
def get_container(request: Request) -> dict:
    return request.app.state.container

# Dependency getters for the Admin module
def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> AuthQueries:
    return container["auth_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> MediaQueries:
    return container["media_queries"]

def get_admin_queries(container: Annotated[dict, Depends(get_container)]) -> AdminQueries:
    return container["admin_queries"]
