"""Adapter implementation for MediaAdminPort."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.admin.application.ports import MediaAdminPort
from src.media_management.application.dtos import (
    DeleteMediaCommand,
    ListMediaQuery,
    PaginatedMedia,
    ReprocessMediaCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.user_management.domain import UserRole


class MediaManagementAdapter(MediaAdminPort):
    """Wrapper around MediaService to implement MediaAdminPort."""

    def __init__(self, media_service: MediaService):
        self._service = media_service

    async def delete_media(
        self,
        command: DeleteMediaCommand,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> None:
        await self._service.delete_media(
            command, user_id=user_id, user_role=user_role
        )

    async def reprocess_media(
        self,
        command: ReprocessMediaCommand,
        user_id: Optional[UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> None:
        await self._service.reprocess_media(
            command, user_id=user_id, user_role=user_role
        )

    async def list_media(self, query: ListMediaQuery) -> PaginatedMedia:
        return await self._service.list_media(query)