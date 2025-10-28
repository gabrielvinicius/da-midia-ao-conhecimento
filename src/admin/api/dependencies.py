# src/admin/api/dependencies.py
from typing import Annotated, Any
from fastapi import Depends, Request

# This file contains only the dependency getters specific to the admin module's API.
from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    return request.app.state.modules


def get_admin_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.admin.admin_queries


def get_auth_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.auth.auth_queries


def get_media_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.media_management.queries


def get_admin_user_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.admin.user_service


def get_admin_media_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.admin.media_service


def get_admin_audit_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    return modules.admin.audit_service
