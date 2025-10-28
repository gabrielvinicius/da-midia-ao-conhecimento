# src/auth/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

# This file contains only the dependency getters specific to the auth module's API.
# Shared security dependencies are now in src/shared/api/dependencies.py
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_user_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.auth.user_service


def get_auth_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.auth.auth_service


def get_auth_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.auth.auth_queries
