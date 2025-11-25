# src/admin/bootstrap.py
"""Helper utilities to bootstrap the admin module."""
from dataclasses import dataclass

from dependency_injector import providers
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.api.dependencies import (
    AdminDependencies,
    get_admin_dependencies,
)
from src.admin.adapters import MediaManagementAdapter, UserManagementAdapter
from src.admin.application.admin_service import AdminService
from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.container import AdminContainer
from src.media_management.application.facade import MediaOrchestrator
from src.media_management.application.queries.media_queries import MediaQueries
from src.user_management.application.queries.auth_queries import AuthQueries


@dataclass
class AdminModule:
    admin_queries: AdminQueries
    audit_service: AdminAuditService
    user_service: AdminUserService
    media_service: AdminMediaService
    service: AdminService


def build_admin_module(
    session: AsyncSession,
    auth_queries: AuthQueries,
    media_queries: MediaQueries,
    media_orchestrator: MediaOrchestrator,
) -> AdminModule:
    container = AdminContainer(db=session)
    container.auth_queries.override(providers.Object(auth_queries))
    container.media_queries.override(providers.Object(media_queries))
    container.media_orchestrator.override(providers.Object(media_orchestrator))

    admin_queries = container.admin_queries()
    audit_service = container.admin_audit_service()
    user_service = container.admin_user_service()
    media_service = container.admin_media_service()

    user_adapter = UserManagementAdapter(
        auth_queries=auth_queries,
        admin_user_service=user_service,
    )
    media_adapter = MediaManagementAdapter(
        media_orchestrator=media_orchestrator,
        admin_media_service=media_service,
    )

    service = AdminService(
        admin_queries=admin_queries,
        audit_service=audit_service,
        auth_queries=auth_queries,
        media_queries=media_queries,
        admin_user_service=user_service,
        admin_media_service=media_service,
        user_adapter=user_adapter,
        media_adapter=media_adapter,
    )

    return AdminModule(
        admin_queries=admin_queries,
        audit_service=audit_service,
        user_service=user_service,
        media_service=media_service,
        service=service,
    )


def bind_admin_module(app: FastAPI, module: AdminModule) -> None:
    """Register dependency overrides for admin APIs."""

    app.dependency_overrides[get_admin_dependencies] = lambda: AdminDependencies(
        admin_queries=module.admin_queries,
        audit_service=module.audit_service,
        user_service=module.user_service,
        media_service=module.media_service,
        service=module.service,
    )


__all__ = [
    "AdminModule",
    "bind_admin_module",
    "build_admin_module",
]
