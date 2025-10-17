# src/storage/application/commands/upload_file_command_handler.py
from uuid import uuid4

from src.storage.application.commands.upload_file_command import UploadFileCommand
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.repositories.storage_repository import StorageRepository
from src.storage.domain.services.file_validator import FileValidator
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class UploadFileCommandHandler:
    """Command handler for file upload (SRP compliance)."""
    
    def __init__(
        self,
        storage_repository: StorageRepository,
        file_validator: FileValidator
    ):
        self._storage_repository = storage_repository
        self._file_validator = file_validator
    
    async def handle(self, command: UploadFileCommand) -> FileMetadata:
        """Handle file upload command with validation."""
        # Create value objects
        file_path = FilePath.from_path(command.file_path)
        file_size = FileSize(len(command.content))
        
        # Domain validation
        self._file_validator.validate_path(file_path)
        self._file_validator.validate_size(file_size)
        self._file_validator.validate_content_type(command.content_type)
        
        # Store file through repository
        metadata = await self._storage_repository.store(file_path, command.content)
        
        return metadata