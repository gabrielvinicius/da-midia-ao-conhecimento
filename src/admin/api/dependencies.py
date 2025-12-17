# src/admin/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.admin.application.services.admin_read_service import AdminReadService
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_service import AdminService
from src.admin.application.services.admin_user_service import AdminUserService
from src.media_management.api.dependencies import get_media_queries
from src.user_management.api.dependencies import get_auth_queries


class AdminDependenciesNotConfiguredError(RuntimeError):
    """Raised when admin dependencies were not bound during bootstrap."""


@dataclass(frozen=True)
class AdminDependencies:
    admin_queries: AdminReadService
    audit_service: AdminAuditService
    user_service: AdminUserService
    media_service: AdminMediaService
    service: AdminService


def get_admin_dependencies() -> AdminDependencies:
    raise AdminDependenciesNotConfiguredError(
        "Admin dependencies are not configured. "
        "Register providers in the lifespan handler."
    )


AdminDeps = Annotated[AdminDependencies, Depends(get_admin_dependencies)]


def get_admin_queries(deps: AdminDeps) -> AdminReadService:
    return deps.admin_queries


def get_admin_user_service(deps: AdminDeps) -> AdminUserService:
    return deps.user_service


def get_admin_media_service(deps: AdminDeps) -> AdminMediaService:
    return deps.media_service


def get_admin_service(deps: AdminDeps) -> AdminService:
    return deps.service


def get_admin_audit_service(deps: AdminDeps) -> AdminAuditService:
    return deps.audit_service


__all__ = [
    "AdminDependencies",
    "AdminDependenciesNotConfiguredError",
    "AdminDeps",
    "get_admin_audit_service",
    "get_admin_dependencies",
    "get_admin_media_service",
    "get_admin_queries",
    "get_admin_user_service",
    "get_admin_service",
    "get_auth_queries",
    "get_media_queries",
]
