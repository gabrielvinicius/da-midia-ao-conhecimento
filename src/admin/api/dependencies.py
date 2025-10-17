# src/admin/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

# This file contains only the dependency getters specific to the admin module's API.

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_admin_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["admin_queries"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["auth_queries"]

def get_media_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["media_queries"]

def get_user_administration_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["user_administration_service"]

def get_delete_media_handler(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["delete_media_handler"]

def get_reprocess_media_handler(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["reprocess_media_handler"]
