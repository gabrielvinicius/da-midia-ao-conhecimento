"""Adapters que conectam o admin ao módulo de media_management."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.admin.application.dtos import BulkReprocessFailedMediaCommand
from src.admin.application.ports import MediaAdminPort
from src.admin.application.services.admin_media_service import AdminMediaService
from src.media_management.application.dtos import (
    CleanupOrphanedFilesCommand,
    DeleteMediaCommand,
    GetMediaStatisticsQuery,
    ListMediaQuery,
    ReprocessMediaCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.user_management.application import UserReadService
from src.user_management.application.dtos import GetUserQuery
from src.user_management.domain import User, UserRole


@dataclass(slots=True)
class MediaManagementAdapter(MediaAdminPort):
    """Wrapper around media queries and admin media service used by the façade."""

    media_service: MediaService
    admin_media_service: AdminMediaService
    auth_queries: UserReadService

    async def list_media(self, query: ListMediaQuery):
        items = await self.media_service.list_media(query=query)
        stats_query = GetMediaStatisticsQuery(search=query.search)
        statistics = await self.media_service.get_media_statistics(query=stats_query)
        total_items = statistics.get("total", 0)
        total_pages = math.ceil(total_items / query.limit) if query.limit else 1
        return {
            "items": items,
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": query.page,
        }

    async def delete_media(self, command: DeleteMediaCommand) -> None:
        admin_user = await self._resolve_admin(command.admin_user_id)
        await self.admin_media_service.delete_media(command.media_id, admin_user)

    async def reprocess_media(self, command: ReprocessMediaCommand) -> None:
        admin_user = await self._resolve_admin(command.admin_user_id)
        await self.admin_media_service.reprocess_media(command.media_id, admin_user)

    async def bulk_reprocess_failed_media(
        self, command: BulkReprocessFailedMediaCommand
    ) -> int:
        admin_user = await self._resolve_admin(command.admin_user_id)
        return await self.admin_media_service.bulk_reprocess_failed_media(admin_user)

    async def cleanup_orphaned_files(self, command: CleanupOrphanedFilesCommand) -> int:
        if not command.actor_id:
            raise PermissionError("actor_id (admin) é obrigatório para cleanup.")
        admin_user = await self._resolve_admin(UUID(command.actor_id))
        return await self.admin_media_service.cleanup_orphaned_files(admin_user)

    async def _resolve_admin(self, admin_id: Optional[UUID]) -> User:
        if not admin_id:
            raise PermissionError(
                "admin_user_id é obrigatório para operações administrativas."
            )
        query = GetUserQuery(user_id=admin_id)
        if hasattr(self.auth_queries, "get_user_by_id"):
            found = await self.auth_queries.get_user_by_id(query)
            if (
                found
                and getattr(found.role, "value", "").upper() == UserRole.ADMIN.value
            ):
                return found
        raise PermissionError("Admin não encontrado ou sem permissão.")
