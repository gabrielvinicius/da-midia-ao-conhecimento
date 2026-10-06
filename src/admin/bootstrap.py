# src/admin/bootstrap.py
"""Helper utilities to bootstrap the admin module."""
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.api.dependencies import AdminDependencies, get_admin_dependencies
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_read_service import AdminReadService
from src.admin.application.services.admin_service import AdminService
from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.infrastructure.adapters.media_read_adapter import MediaReadAdapter
from src.admin.infrastructure.adapters.user_read_adapter import UserReadAdapter
from src.admin.infrastructure.dependencies.providers import (
    get_media_admin_adapter,
    get_media_read_adapter,
    get_user_admin_adapter,
    get_user_read_adapter,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.dependencies.builders import build_media_read_service
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.user_service import UserService
from src.user_management.application.services.permission_service import (
    UserPermissionService,
)


@dataclass
class AdminModule:
    admin_queries: AdminReadService
    audit_service: AdminAuditService
    user_service: AdminUserService
    media_service: AdminMediaService
    service: AdminService


from src.shared.infrastructure.repositories.processing_stats_repository import (
    ProcessingStatsRepository,
)

def build_admin_module(
    session: AsyncSession,
    auth_queries: UserReadService,
    user_service_core: UserService, # Core service
    media_service_core: MediaService, # Core service
) -> AdminModule:
    # Core components (no DI container)
    permission_service = UserPermissionService()
    audit_service = AdminAuditService()

    # Read adapters via ports
    media_read_adapter: MediaReadAdapter = get_media_read_adapter(build_media_read_service(session))
    user_read_adapter: UserReadAdapter = get_user_read_adapter(auth_queries)
    admin_queries = AdminReadService(
        user_read_port=user_read_adapter,
        media_read_port=media_read_adapter,
    )

    # Os módulos de mídias e de usuários, vistos pelas portas do admin.
    media_admin_adapter = get_media_admin_adapter(media_service_core, session)
    user_admin_adapter = get_user_admin_adapter(user_service_core, auth_queries)

    # Services
    user_service = AdminUserService(
        user_service=user_admin_adapter,
        permission_service=permission_service,
        audit_service=audit_service,
    )
    admin_media_service = AdminMediaService(
        media=media_admin_adapter,
        permission_service=permission_service,
        audit_service=audit_service,
    )

    service = AdminService(
        admin_read_service=admin_queries,
        audit_service=audit_service,
        admin_user_service=user_service,
        admin_media_service=admin_media_service,
        processing_stats=ProcessingStatsRepository(session) if session is not None else None,
    )

    return AdminModule(
        admin_queries=admin_queries,
        audit_service=audit_service,
        user_service=user_service,
        media_service=admin_media_service,
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
