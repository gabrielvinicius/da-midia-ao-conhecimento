# src/admin/bootstrap.py
"""Helper utilities to bootstrap the admin module."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from dependency_injector import providers

from src.admin.adapters import MediaManagementAdapter, UserManagementAdapter
from src.admin.application.admin_service import AdminService
from src.admin.container import AdminContainer
from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.user_management.application.queries.auth_queries import AuthQueries
from src.media_management.application.facade import MediaManagementFacade
from src.media_management.application.queries.media_queries import MediaQueries


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
    media_facade: MediaManagementFacade,
) -> AdminModule:
    container = AdminContainer(db=session)
    container.auth_queries.override(providers.Object(auth_queries))
    container.media_queries.override(providers.Object(media_queries))
    container.media_facade.override(providers.Object(media_facade))

    admin_queries = container.admin_queries()
    audit_service = container.admin_audit_service()
    user_service = container.admin_user_service()
    media_service = container.admin_media_service()

    user_adapter = UserManagementAdapter(
        auth_queries=auth_queries,
        admin_user_service=user_service,
    )
    media_adapter = MediaManagementAdapter(
        media_facade=media_facade,
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
