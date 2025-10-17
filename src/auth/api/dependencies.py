# src/auth/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

# This file contains only the dependency getters specific to the auth module's API.
# Shared security dependencies are now in src/shared/api/dependencies.py

def get_container(request: Request) -> dict:
    return request.app.state.container

def get_user_registration_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["user_registration_service"]

def get_authentication_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["authentication_service"]

def get_auth_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    return container["auth_queries"]
