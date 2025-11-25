"""Unified media application service.

This service consolidates the responsibilities that used to be scattered
across ``MediaUploadService``, ``MediaLifecycleService`` and
``MediaQueryService`` so that HTTP handlers and admin modules have a single
entrypoint for CRUD-style media flows.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.media_management.application.commands.commands import (
    DeleteMediaCommand,
    ReprocessMediaCommand,
)
from src.media_management.application.commands.create_media_command import (
    CreateMediaCommand,
)
from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.validators import MediaUploadValidator
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.user_management.domain.user import UserRole


class MediaService:
    """Orchestrates all user-facing media operations."""

    def __init__(
        self,
        *,
        media_queries: MediaQueries,
        create_media_handler: CreateMediaCommandHandler,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler,
        upload_validator: MediaUploadValidator,
        access_policy: MediaAccessPolicy,
    ) -> None:
        self._media_queries = media_queries
        self._create_media_handler = create_media_handler
        self._delete_media_handler = delete_media_handler
        self._reprocess_media_handler = reprocess_media_handler
        self._upload_validator = upload_validator
        self._access_policy = access_policy

    # ------------------------------------------------------------------
    # Creation flows
    # ------------------------------------------------------------------
    async def upload_media(
        self,
        *,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        storage_provider: str,
        transcription_provider: Optional[str] = None,
        summarization_provider: Optional[str] = None,
        sentiment_provider: Optional[str] = None,
        topic_modeling_provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate inputs and dispatch the create media command."""

        self._upload_validator.validate(file_content, filename)

        command = CreateMediaCommand(
            user_id=str(user_id),
            file=file_content,
            filename=filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
            metadata=metadata,
        )

        return await self._create_media_handler.handle(command)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------
    async def _require_media(self, media_id: UUID) -> Media:
        media = await self._media_queries.get_by_id(media_id)
        if media is None:
            raise ValueError(f"Media {media_id} not found")
        return media

    async def list_media(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> List[Media]:
        return await self._media_queries.list_all(
            page=page,
            limit=limit,
            status=status,
            search=search,
            user_id=user_id,
        )

    async def list_media_for_user(
        self,
        *,
        user_id: UUID,
        status: Optional[MediaStatus] = None,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[Media]:
        return await self.list_media(
            user_id=user_id,
            status=status,
            page=page,
            limit=limit,
            search=search,
        )

    async def get_media(self, media_id: UUID) -> Media:
        return await self._require_media(media_id)

    def _ensure_access(
        self,
        media: Media,
        user_id: Optional[UUID],
        user_role: Optional[UserRole],
    ) -> UUID:
        effective_user = user_id
        if effective_user is None:
            if user_role == UserRole.ADMIN:
                effective_user = media.user_id
            else:
                raise PermissionError("User identifier is required for non-admin operations")

        self._access_policy.ensure_can_access(media, effective_user, user_role)
        return effective_user

    async def get_media_for_user(
        self,
        *,
        media_id: UUID,
        user_id: Optional[UUID],
        user_role: Optional[UserRole] = None,
    ) -> Media:
        media = await self._require_media(media_id)
        self._ensure_access(media, user_id, user_role)
        return media

    async def get_media_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        if user_id:
            total = await self._media_queries.count_by_user(user_id)
            by_status: Dict[str, int] = {}
            for status in MediaStatus:
                count = await self._media_queries.count_by_user_and_status(user_id, status)
                by_status[status.value] = count
        else:
            total = await self._media_queries.count_all()
            by_status = {}
            for status in MediaStatus:
                count = await self._media_queries.count_by_status(status)
                by_status[status.value] = count

        return {"total": total, "by_status": by_status}

    # ------------------------------------------------------------------
    # Mutating operations
    # ------------------------------------------------------------------
    async def delete_media(
        self,
        *,
        media_id: UUID,
        user_id: Optional[UUID],
        user_role: Optional[UserRole] = None,
    ) -> Media:
        media = await self._require_media(media_id)
        self._ensure_access(media, user_id, user_role)
        await self._delete_media_handler.handle(DeleteMediaCommand(media_id=media_id))
        return media

    async def reprocess_media(
        self,
        *,
        media_id: UUID,
        user_id: Optional[UUID],
        user_role: Optional[UserRole] = None,
    ) -> Media:
        media = await self._require_media(media_id)
        self._ensure_access(media, user_id, user_role)
        await self._reprocess_media_handler.handle(ReprocessMediaCommand(media_id=media_id))
        return media


__all__ = ["MediaService"]
