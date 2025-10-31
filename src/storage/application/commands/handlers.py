"""
Storage Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.storage.domain.interfaces import IStorageService
from .commands import (
    StoreFileCommand,
    DeleteFileCommand,
    MoveFileCommand,
    ValidateFileCommand
)

logger = structlog.get_logger(__name__)


class StoreFileCommandHandler:
    """Handler for store file command"""
    
    def __init__(self, storage_service: IStorageService):
        self.storage_service = storage_service

    async def handle(self, command: StoreFileCommand) -> Dict[str, Any]:
        """Execute file storage command"""
        logger.info("storage.store.started", file_path=command.file_path)
        
        try:
            result = await self.storage_service.store(
                file_data=command.file_data,
                file_path=command.file_path,
                content_type=command.content_type,
                metadata=command.metadata
            )
            
            logger.info("storage.store.completed", file_path=command.file_path)
            
            return {
                "success": True,
                "file_path": command.file_path,
                "size": len(command.file_data),
                "result": result,
                "message": "File stored successfully"
            }
            
        except Exception as e:
            logger.error("storage.store.failed", file_path=command.file_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"File storage failed: {str(e)}"
            }


class DeleteFileCommandHandler:
    """Handler for delete file command"""
    
    def __init__(self, storage_service: IStorageService):
        self.storage_service = storage_service

    async def handle(self, command: DeleteFileCommand) -> Dict[str, Any]:
        """Execute file deletion command"""
        logger.info("storage.delete.started", file_path=command.file_path)
        
        try:
            await self.storage_service.delete(command.file_path)
            
            logger.info("storage.delete.completed", file_path=command.file_path)
            
            return {
                "success": True,
                "file_path": command.file_path,
                "message": "File deleted successfully"
            }
            
        except Exception as e:
            logger.error("storage.delete.failed", file_path=command.file_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"File deletion failed: {str(e)}"
            }


class MoveFileCommandHandler:
    """Handler for move file command"""
    
    def __init__(self, storage_service: IStorageService):
        self.storage_service = storage_service

    async def handle(self, command: MoveFileCommand) -> Dict[str, Any]:
        """Execute file move command"""
        logger.info("storage.move.started", source=command.source_path, destination=command.destination_path)
        
        try:
            await self.storage_service.move(
                source_path=command.source_path,
                destination_path=command.destination_path,
                overwrite=command.overwrite
            )
            
            logger.info("storage.move.completed", source=command.source_path, destination=command.destination_path)
            
            return {
                "success": True,
                "source_path": command.source_path,
                "destination_path": command.destination_path,
                "message": "File moved successfully"
            }
            
        except Exception as e:
            logger.error("storage.move.failed", source=command.source_path, destination=command.destination_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"File move failed: {str(e)}"
            }


class ValidateFileCommandHandler:
    """Handler for validate file command"""
    
    def __init__(self, storage_service: IStorageService):
        self.storage_service = storage_service

    async def handle(self, command: ValidateFileCommand) -> Dict[str, Any]:
        """Execute file validation command"""
        logger.info("storage.validate.started", file_path=command.file_path)
        
        try:
            is_valid = await self.storage_service.validate(
                file_path=command.file_path,
                expected_checksum=command.expected_checksum
            )
            
            logger.info("storage.validate.completed", file_path=command.file_path, is_valid=is_valid)
            
            return {
                "success": True,
                "file_path": command.file_path,
                "is_valid": is_valid,
                "message": "File validation completed"
            }
            
        except Exception as e:
            logger.error("storage.validate.failed", file_path=command.file_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"File validation failed: {str(e)}"
            }