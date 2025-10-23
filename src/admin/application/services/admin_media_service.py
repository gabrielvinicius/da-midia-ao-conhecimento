"""
Admin Media Service - Single Responsibility: Admin media operations
Follows SRP by handling only admin-related media management.
"""
from typing import List, Any
from uuid import UUID
import structlog

from src.admin.domain.interfaces import IAdminMediaService, IAdminAuditService
from src.auth.domain.user import User
from src.media_management.domain.media import Media, MediaStatus
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.commands.delete_media_command import DeleteMediaCommand
from src.media_management.application.commands.delete_media_command_handler import DeleteMediaCommandHandler
from src.media_management.application.commands.reprocess_media_command import ReprocessMediaCommand
from src.media_management.application.commands.reprocess_media_command_handler import ReprocessMediaCommandHandler

logger = structlog.get_logger(__name__)


class AdminMediaService(IAdminMediaService):
    """
    Service responsible ONLY for admin media management operations.
    
    Single Responsibility: Handle admin operations on media.
    Open/Closed: Extensible through command handlers and interfaces.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        media_repository: MediaRepository,
        permission_service: Any, # IUserPermissionService has no implementation
        audit_service: IAdminAuditService,
        delete_media_handler: DeleteMediaCommandHandler,
        reprocess_media_handler: ReprocessMediaCommandHandler
    ):
        self.media_repository = media_repository
        self.permission_service = permission_service
        self.audit_service = audit_service
        self.delete_media_handler = delete_media_handler
        self.reprocess_media_handler = reprocess_media_handler
    
    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        """
        Delete media with admin validation and audit logging.
        
        Args:
            media_id: ID of media to delete
            admin_user: Admin user performing the operation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found
        """
        # Validate admin permissions (basic check)
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can delete media")
        
        # Get media for audit log
        media = await self.media_repository.find_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")
        
        # Execute delete command
        command = DeleteMediaCommand(media_id=media_id)
        await self.delete_media_handler.handle(command)
        
        # Log admin action
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
        """
        Reprocess failed media with admin validation and audit logging.
        
        Args:
            media_id: ID of media to reprocess
            admin_user: Admin user performing the operation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found or not in failed state
        """
        # Validate admin permissions
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can reprocess media")
        
        # Get media for validation and audit log
        media = await self.media_repository.find_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")
        
        if media.status != MediaStatus.FAILED:
            raise ValueError(f"Media {media_id} is not in failed state (current: {media.status.value})")
        
        # Execute reprocess command
        command = ReprocessMediaCommand(media_id=media_id)
        await self.reprocess_media_handler.handle(command)
        
        # Log admin action
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
        """
        Reprocess all failed media items in bulk.
        
        Args:
            admin_user: Admin user performing the operation
            
        Returns:
            Number of media items queued for reprocessing
            
        Raises:
            PermissionError: If admin doesn't have permission
        """
        # Validate admin permissions
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can bulk reprocess media")
        
        # Get all failed media
        failed_media = await self.get_media_by_status(MediaStatus.FAILED)
        
        reprocessed_count = 0
        for media in failed_media:
            try:
                await self.reprocess_media(media.id, admin_user)
                reprocessed_count += 1
            except Exception as e:
                logger.warning(
                    "admin.media.bulk_reprocess.failed",
                    media_id=str(media.id),
                    error=str(e),
                    admin_id=str(admin_user.id)
                )
                continue
        
        # Log bulk action
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
        """
        Clean up orphaned files in storage (files without corresponding media records).
        
        Args:
            admin_user: Admin user performing the operation
            
        Returns:
            Number of orphaned files cleaned up
            
        Raises:
            PermissionError: If admin doesn't have permission
        """
        # Validate admin permissions
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can cleanup orphaned files")
        
        # This is a placeholder implementation
        # In a real system, this would:
        # 1. List all files in storage
        # 2. Compare with media records in database
        # 3. Delete files that don't have corresponding records
        # 4. Handle concurrent access and safety checks
        
        cleaned_count = 0  # Placeholder
        
        # Log cleanup action
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
        """
        Get media items by processing status.
        
        Args:
            status: Media status to filter by
            
        Returns:
            List of media items with the specified status
        """
        # This would be implemented in the media repository
        # For now, return empty list as placeholder
        return []
    
    async def get_media_processing_queue_info(self) -> dict:
        """
        Get information about media processing queue.
        
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
            "oldest_processing": None,  # Would get oldest processing item
            "oldest_failed": None,      # Would get oldest failed item
        }
    
    async def force_media_status_change(
        self, 
        media_id: UUID, 
        new_status: MediaStatus, 
        admin_user: User,
        reason: str
    ) -> None:
        """
        Force change media status (emergency admin action).
        
        Args:
            media_id: ID of media to update
            new_status: New status to set
            admin_user: Admin user performing the operation
            reason: Reason for the status change
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If media not found
        """
        # Validate admin permissions
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can force status changes")
        
        # Get media
        media = await self.media_repository.find_by_id(media_id)
        if not media:
            raise ValueError(f"Media with id {media_id} not found")
        
        old_status = media.status
        
        # Update status
        media.status = new_status
        await self.media_repository.save(media)
        
        # Log admin action
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