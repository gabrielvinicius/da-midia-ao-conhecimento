"""
Admin Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.application.queries.user_queries import UserQueries
from .commands import (
    DeleteMediaCommand,
    DeleteUserCommand,
    ReprocessMediaCommand,
    UpdateUserRoleCommand
)

logger = structlog.get_logger(__name__)


class DeleteMediaCommandHandler:
    """Handler for delete media command"""
    
    def __init__(
        self,
        media_repository: MediaRepository,
        media_queries: MediaQueries,
        storage_service_factory: StorageServiceFactory,
    ):
        self.media_repository = media_repository
        self.media_queries = media_queries
        self.storage_service_factory = storage_service_factory

    async def handle(self, command: DeleteMediaCommand) -> Dict[str, Any]:
        """Execute media deletion command"""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            raise ValueError("Media not found.")

        # Delete file from storage
        try:
            storage_service = self.storage_service_factory.create_storage_service(media.storage_provider)
            await storage_service.delete(media.original_file_path)
            logger.info("media.file.deleted", path=media.original_file_path)
        except Exception as e:
            logger.error("media.file.delete_failed", path=media.original_file_path, error=str(e))

        # Delete database record
        success = await self.media_repository.delete(command.media_id)
        if not success:
            raise ValueError("Media record could not be deleted.")
            
        return {
            "success": True,
            "media_id": str(command.media_id),
            "admin_user_id": str(command.admin_user_id) if command.admin_user_id else None,
            "reason": command.reason
        }


class DeleteUserCommandHandler:
    """Handler for delete user command"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        user_queries: UserQueries,
    ):
        self.user_repository = user_repository
        self.user_queries = user_queries

    async def handle(self, command: DeleteUserCommand) -> Dict[str, Any]:
        """Execute user deletion command"""
        user = await self.user_queries.get_by_id(str(command.user_id))
        if not user:
            raise ValueError("User not found.")

        success = await self.user_repository.delete(command.user_id)
        if not success:
            raise ValueError("User could not be deleted.")
            
        logger.info("admin.user.deleted", 
                   user_id=str(command.user_id),
                   admin_user_id=str(command.admin_user_id),
                   reason=command.reason)
            
        return {
            "success": True,
            "user_id": str(command.user_id),
            "admin_user_id": str(command.admin_user_id),
            "reason": command.reason
        }


class ReprocessMediaCommandHandler:
    """Handler for reprocess media command"""
    
    def __init__(
        self,
        media_repository: MediaRepository,
        media_queries: MediaQueries,
    ):
        self.media_repository = media_repository
        self.media_queries = media_queries

    async def handle(self, command: ReprocessMediaCommand) -> Dict[str, Any]:
        """Execute media reprocessing command"""
        media = await self.media_queries.get_by_id(str(command.media_id))
        if not media:
            raise ValueError("Media not found.")

        updated_media = await self.media_repository.update_status(
            command.media_id, 
            "processing"
        )
        
        logger.info("admin.media.reprocess_triggered", 
                   media_id=str(command.media_id),
                   admin_user_id=str(command.admin_user_id),
                   force=command.force)
            
        return {
            "success": True,
            "media_id": str(command.media_id),
            "admin_user_id": str(command.admin_user_id),
            "force": command.force,
            "status": "processing"
        }


class UpdateUserRoleCommandHandler:
    """Handler for update user role command"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        user_queries: UserQueries,
    ):
        self.user_repository = user_repository
        self.user_queries = user_queries

    async def handle(self, command: UpdateUserRoleCommand) -> Dict[str, Any]:
        """Execute user role update command"""
        user = await self.user_queries.get_by_id(str(command.user_id))
        if not user:
            raise ValueError("User not found.")

        updated_user = await self.user_repository.update_role(
            command.user_id, 
            command.new_role
        )
        
        logger.info("admin.user.role_updated", 
                   user_id=str(command.user_id),
                   old_role=user.role,
                   new_role=command.new_role,
                   admin_user_id=str(command.admin_user_id),
                   reason=command.reason)
            
        return {
            "success": True,
            "user_id": str(command.user_id),
            "old_role": user.role,
            "new_role": command.new_role,
            "admin_user_id": str(command.admin_user_id),
            "reason": command.reason
        }