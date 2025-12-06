"""Administrative media management services."""

from typing import List, Optional
from uuid import UUID

import structlog

from src.admin.domain.interfaces import IAdminAuditService, IAdminMediaService
from src.media_management.application.services.media_service import MediaService
from src.shared.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.media_management.infrastructure.repositories import MediaRepository
from src.user_management.domain.interfaces import IUserPermissionService
from src.user_management.domain.user import User
from src.media_management.application.commands.dto import DeleteMediaCommand, ReprocessMediaCommand, CleanupOrphanedFilesCommand
from src.user_management.domain.user import UserRole


logger = structlog.get_logger(__name__)


class AdminMediaService(IAdminMediaService):
    """Service responsible ONLY for admin media management operations.
    
    Single Responsibility: Handle admin operations on media.
    Open/Closed: Extensible through command handlers and interfaces.
    Dependency Inversion: Depends on abstractions, not concretions.
    """

    def __init__(
        self,
        media_repository: MediaRepository,
        permission_service: IUserPermissionService,
        audit_service: IAdminAuditService,
        media_service: MediaService,
    ):
        self.media_repository = media_repository
        self.permission_service = permission_service
        self.audit_service = audit_service
        self.media_service = media_service

    async def _dispatch_admin_delete(
        self,
        media_id: UUID,
        *,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        """Bridge admin deletions to the consolidated media service."""
        await self.media_service.delete_media(
            command=DeleteMediaCommand(media_id=media_id),
            user_id=UUID(actor_id) if actor_id else None,
            user_role=UserRole.ADMIN,
        )

    async def _dispatch_admin_reprocess(
        self,
        media_id: UUID,
        *,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        """Bridge admin reprocess requests to the consolidated media service."""
        await self.media_service.reprocess_media(
            command=ReprocessMediaCommand(media_id=media_id),
            user_id=UUID(actor_id) if actor_id else None,
            user_role=UserRole.ADMIN,
        )

    async def _dispatch_bulk_reprocess(self, failed_media: List[Media], admin_user: User) -> int:
        """Execute bulk reprocess leveraging the consolidated media service."""
        reprocessed_count = 0
        for media_item in failed_media:
            try:
                await self.media_service.reprocess_media(
                    command=ReprocessMediaCommand(media_id=media_item.id),
                    user_id=admin_user.id,
                    user_role=UserRole.ADMIN,
                )
                reprocessed_count += 1
            except Exception as exc:
                logger.warning(
                    "admin.media.bulk_reprocess_failed_single_item",
                    media_id=str(media_item.id),
                    error=str(exc),
                )
        return reprocessed_count

    async def _dispatch_cleanup_orphans(self, admin_user: User) -> int:
        """Delegate orphan cleanup to the consolidated media service."""
        return await self.media_service.cleanup_orphaned_files(
            command=CleanupOrphanedFilesCommand(actor_id=str(admin_user.id))
        )

    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        """Delete media with admin validation and audit logging.
        
        Args:
            media_id: ID of media to delete
            admin_user: Admin user performing the operation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found

        """
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")

        self.permission_service.validate_admin_operation(admin_user, media.user_id)

        await self._dispatch_admin_delete(
            media_id,
            actor_id=str(admin_user.id),
        )

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="delete_media",
            target_type="media",
            target_id=media_id,
            details={
                "filename": media.filename,
                "media_type": media.media_type.value,
                "status": media.status.value,
                "owner_id": str(media.user_id)
            }
        )

        logger.info(
            "admin.media.deleted",
            admin_id=str(admin_user.id),
            media_id=str(media_id),
            filename=media.filename
        )

    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        """Reprocess failed media with admin validation and audit logging.
        
        Args:
            media_id: ID of media to reprocess
            admin_user: Admin user performing the operation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found or not in failed state

        """
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")

        self.permission_service.validate_admin_operation(admin_user, media.user_id)

        if media.status != MediaStatus.FAILED:
            raise ValueError(f"Media {media_id} is not in failed state (current: {media.status.value})")

        await self._dispatch_admin_reprocess(
            media_id,
            actor_id=str(admin_user.id),
        )

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="reprocess_media",
            target_type="media",
            target_id=media_id,
            details={
                "filename": media.filename,
                "media_type": media.media_type.value,
                "previous_status": media.status.value,
                "owner_id": str(media.user_id)
            }
        )

        logger.info(
            "admin.media.reprocess_initiated",
            admin_id=str(admin_user.id),
            media_id=str(media_id),
            filename=media.filename
        )

    async def bulk_reprocess_failed_media(self, admin_user: User) -> int:
        """Reprocess all failed media items in bulk.
        
        Args:
            admin_user: Admin user performing the operation
            
        Returns:
            Number of media items queued for reprocessing
            
        Raises:
            PermissionError: If admin doesn't have permission

        """
        self.permission_service.validate_admin_operation(
            admin_user,
            admin_user.id,
        )  # Pass admin_user.id as target_user_id

        failed_media = await self.get_media_by_status(MediaStatus.FAILED)
        reprocessed_count = await self._dispatch_bulk_reprocess(failed_media, admin_user)

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="bulk_reprocess_failed_media",
            target_type="system",
            target_id=admin_user.id,  # System action, use admin ID as target
            details={
                "total_failed": len(failed_media),
                "reprocessed_count": reprocessed_count
            }
        )

        logger.info(
            "admin.media.bulk_reprocess_completed",
            admin_id=str(admin_user.id),
            total_failed=len(failed_media),
            reprocessed_count=reprocessed_count
        )

        return reprocessed_count

    async def cleanup_orphaned_files(self, admin_user: User) -> int:
        """Clean up orphaned files in storage (files without corresponding media records).
        
        Args:
            admin_user: Admin user performing the operation
            
        Returns:
            Number of orphaned files cleaned up
            
        Raises:
            PermissionError: If admin doesn't have permission

        """
        self.permission_service.validate_admin_operation(admin_user, admin_user.id)

        cleaned_count = await self._dispatch_cleanup_orphans(admin_user)

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="cleanup_orphaned_files",
            target_type="system",
            target_id=admin_user.id,
            details={
                "cleaned_files_count": cleaned_count
            }
        )

        logger.info(
            "admin.media.cleanup_completed",
            admin_id=str(admin_user.id),
            cleaned_count=cleaned_count
        )

        return cleaned_count

    async def get_media_by_status(self, status: MediaStatus) -> List[Media]:
        """Get media items by processing status.
        
        Args:
            status: Media status to filter by
            
        Returns:
            List of media items with the specified status

        """
        return await self.media_repository.list_all(status=status)

    async def get_media_processing_queue_info(self) -> dict:
        """Get information about media processing queue.
        
        Returns:
            Dictionary with queue statistics

        """
        processing_media = await self.get_media_by_status(MediaStatus.PROCESSING)
        failed_media = await self.get_media_by_status(MediaStatus.FAILED)
        uploaded_media = await self.get_media_by_status(MediaStatus.UPLOADED)

        return {
            "processing_count": len(processing_media),
            "failed_count": len(failed_media),
            "queued_count": len(uploaded_media),
            "oldest_processing": min(media.created_at for media in processing_media) if processing_media else None,
            "oldest_failed": min(media.created_at for media in failed_media) if failed_media else None,
        }

    async def force_media_status_change(
        self,
        media_id: UUID,
        new_status: MediaStatus,
        admin_user: User,
        reason: str
    ) -> None:
        """Force change media status (emergency admin action).
        
        Args:
            media_id: ID of media to update
            new_status: New status to set
            admin_user: Admin user performing the operation
            reason: Reason for the status change
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found

        """
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")

        self.permission_service.validate_admin_operation(admin_user, media.user_id)

        old_status = media.status

        media.status = new_status
        await self.media_repository.update(media)

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="force_media_status_change",
            target_type="media",
            target_id=media_id,
            details={
                "filename": media.filename,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason
            }
        )

        logger.warning(
            "admin.media.force_status_change",
            admin_id=str(admin_user.id),
            media_id=str(media_id),
            old_status=old_status.value,
            new_status=new_status.value,
            reason=reason
        )
