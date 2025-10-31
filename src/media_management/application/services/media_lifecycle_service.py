"""Service that coordinates media lifecycle transitions."""

from typing import Optional
from uuid import UUID

from src.user_management.domain.user import UserRole
from src.media_management.application.commands.commands import (
    DeleteMediaCommand,
    ReprocessMediaCommand,
)
from src.media_management.application.commands.handlers import (
    DeleteMediaCommandHandler,
    ReprocessMediaCommandHandler,
)
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository import MediaRepository


class MediaLifecycleService:
    """Encapsulates operations that mutate media state."""

    def __init__(
        self,
        media_repository: MediaRepository,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler,
        access_policy: MediaAccessPolicy,
    ) -> None:
        self._media_repository = media_repository
        self._delete_media_handler = delete_media_handler
        self._reprocess_media_handler = reprocess_media_handler
        self._access_policy = access_policy

    async def delete_media(
        self, media_id: UUID, user_id: UUID, user_role: Optional[UserRole] = None
    ) -> None:
        """Ensure permissions then dispatch the delete command."""

        media = await self._media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")

        self._access_policy.ensure_can_access(media, user_id, user_role)
        await self._delete_media_handler.handle(DeleteMediaCommand(media_id=media_id))

    async def reprocess_media(
        self, media_id: UUID, user_id: UUID, user_role: Optional[UserRole] = None
    ) -> None:
        """Ensure permissions then dispatch the reprocess command."""

        media = await self._media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")

        self._access_policy.ensure_can_access(media, user_id, user_role)
        await self._reprocess_media_handler.handle(ReprocessMediaCommand(media_id=media_id))

    async def reset_for_reprocessing(self, media_id: UUID) -> Media:
        """Reset the media status to uploaded prior to a new processing run."""

        media = await self._media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")

        if media.status != MediaStatus.FAILED:
            raise ValueError(
                f"Media is not in FAILED state. Current: {media.status}"
            )

        updated_media = await self._media_repository.update_status(
            media_id,
            MediaStatus.UPLOADED,
            error_message=None,
        )
        await self._media_repository.save(updated_media)
        return updated_media

    async def update_status(
        self,
        media_id: UUID,
        status: MediaStatus,
        error_message: Optional[str] = None,
    ) -> Media:
        """Update a media record status and optional error information."""

        media = await self._media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media {media_id} not found")

        updated_media = await self._media_repository.update_status(
            media_id,
            status,
            error_message=error_message,
        )
        if error_message is not None:
            await self._media_repository.save(updated_media)
        return updated_media
