# src/admin/bootstrap.py
"""Helper utilities to bootstrap the admin module."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from dependency_injector import providers

from src.admin.container import AdminContainer
from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.auth.application.queries.auth_queries import AuthQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)


@dataclass
class AdminModule:
    admin_queries: AdminQueries
    audit_service: AdminAuditService
    user_service: AdminUserService
    media_service: AdminMediaService


def build_admin_module(
    session: AsyncSession,
    auth_queries: AuthQueries,
    media_queries: MediaQueries,
    delete_media_handler: DeleteMediaCommandHandler,
    reprocess_media_handler: ReprocessMediaCommandHandler,
) -> AdminModule:
    container = AdminContainer(db=session)
    container.auth_queries.override(providers.Object(auth_queries))
    container.media_queries.override(providers.Object(media_queries))
    container.delete_media_handler.override(providers.Object(delete_media_handler))
    container.reprocess_media_handler.override(providers.Object(reprocess_media_handler))

    return AdminModule(
        admin_queries=container.admin_queries(),
        audit_service=container.admin_audit_service(),
        user_service=container.admin_user_service(),
        media_service=container.admin_media_service(),
    )
