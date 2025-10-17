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

def get_admin_user_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["admin_user_service"]

def get_admin_media_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["admin_media_service"]

def get_admin_audit_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["admin_audit_service"]
