# src/admin/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.application.services.admin_read_service import AdminReadService
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_service import AdminService
from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.infrastructure.dependencies.providers import (
    get_media_admin_adapter,
    get_media_read_adapter,
    get_user_admin_adapter,
    get_user_read_adapter,
)
from src.media_management.api.dependencies import get_media_service
from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.shared.infrastructure.database.db import get_db
from src.user_management.api.dependencies import get_auth_queries
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.permission_service import (
    UserPermissionService,
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)
from src.admin.infrastructure.adapters.user_repository_adapter import (
    UserRepositoryAdapter,
)
from src.admin.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)


class AdminDependenciesNotConfiguredError(RuntimeError):
    """Raised when admin dependencies were not bound during bootstrap."""


@dataclass(frozen=True)
class AdminDependencies:
    admin_queries: AdminReadService
    audit_service: AdminAuditService
    user_service: AdminUserService
    media_service: AdminMediaService
    service: AdminService


def get_admin_dependencies(
    session: AsyncSession = Depends(get_db),
    auth_queries: UserReadService = Depends(get_auth_queries),
    media_service: MediaService = Depends(get_media_service),
) -> AdminDependencies:
    """Provider padrão (por request) para o módulo admin.

    Evita compartilhar AsyncSession globalmente entre requests.
    """

    permission_service = UserPermissionService()
    audit_service = AdminAuditService()

    user_repo_adapter = UserRepositoryAdapter(UserRepository(db=session))
    media_repo = MediaRepository(db=session)
    media_repo_adapter = MediaRepositoryAdapter(media_repo)

    media_read_adapter = get_media_read_adapter(media_repo_adapter)
    user_read_adapter = get_user_read_adapter(auth_queries)
    admin_queries = AdminReadService(
        user_read_port=user_read_adapter,
        media_read_port=media_read_adapter,
    )

    user_service = AdminUserService(
        user_repository=user_repo_adapter,
        permission_service=permission_service,
        audit_service=audit_service,
    )
    admin_media_service = AdminMediaService(
        media_repository=media_repo_adapter,
        permission_service=permission_service,
        audit_service=audit_service,
        media_service=media_service,
    )

    user_adapter = get_user_admin_adapter(
        auth_queries=auth_queries,
        admin_user_service=user_service,
    )
    media_adapter = get_media_admin_adapter(
        media_service=media_service,
        admin_media_service=admin_media_service,
        auth_queries=auth_queries,
    )

    service = AdminService(
        admin_read_service=admin_queries,
        audit_service=audit_service,
        admin_user_service=user_service,
        admin_media_service=admin_media_service,
        user_adapter=user_adapter,
        media_adapter=media_adapter,
    )

    return AdminDependencies(
        admin_queries=admin_queries,
        audit_service=audit_service,
        user_service=user_service,
        media_service=admin_media_service,
        service=service,
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
]
