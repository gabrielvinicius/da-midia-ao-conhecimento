"""
Consolidated Storage Service
Consolidates: StorageService, EnhancedStorageService, StorageMetricsService
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.storage.application.commands.commands import (
    StoreFileCommand,
    DeleteFileCommand,
    MoveFileCommand,
    ValidateFileCommand
)
from src.storage.application.commands.handlers import (
    StoreFileCommandHandler,
    DeleteFileCommandHandler,
    MoveFileCommandHandler,
    ValidateFileCommandHandler
)

logger = structlog.get_logger(__name__)


class StorageService:
    """Consolidated service for all storage operations."""
    
    def __init__(
        self,
        store_file_handler: StoreFileCommandHandler,
        delete_file_handler: DeleteFileCommandHandler,
        move_file_handler: MoveFileCommandHandler,
        validate_file_handler: ValidateFileCommandHandler
    ):
        self.store_file_handler = store_file_handler
        self.delete_file_handler = delete_file_handler
        self.move_file_handler = move_file_handler
        self.validate_file_handler = validate_file_handler

    async def store_file(self, file_data: bytes, file_path: str, content_type: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store file with validation."""
        command = StoreFileCommand(
            file_data=file_data,
            file_path=file_path,
            content_type=content_type,
            metadata=metadata
        )
        return await self.store_file_handler.handle(command)
    
    async def delete_file(self, file_path: str, force: bool = False) -> Dict[str, Any]:
        """Delete file."""
        command = DeleteFileCommand(file_path=file_path, force=force)
        return await self.delete_file_handler.handle(command)
    
    async def move_file(self, source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move file."""
        command = MoveFileCommand(
            source_path=source_path,
            destination_path=destination_path,
            overwrite=overwrite
        )
        return await self.move_file_handler.handle(command)