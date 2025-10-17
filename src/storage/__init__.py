# src/storage/__init__.py
"""
Storage module following SOLID principles.

This module provides a clean, extensible storage abstraction that follows:
- SRP: Each class has a single responsibility
- OCP: Easy to extend with new providers without modification
- LSP: All providers implement the same interface contract
- ISP: Segregated interfaces for different concerns
- DIP: High-level modules depend on abstractions

Usage:
    from src.storage import get_storage_repository
    
    # Get repository (auto-configured from environment)
    repository = get_storage_repository()
    
    # Store a file
    file_path = FilePath.from_path("documents/file.pdf")
    metadata = await repository.store(file_path, file_content)
    
    # Retrieve a file
    content = await repository.retrieve(file_path)
"""

# Domain exports
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize
from src.storage.domain.interfaces import (
    StorageRepository,
    StorageProvider,
    StorageProviderFactory,
    StorageConfiguration
)

# Application exports
from src.storage.application.commands.upload_file_command import UploadFileCommand
from src.storage.application.commands.upload_file_command_handler import UploadFileCommandHandler
from src.storage.application.queries.get_file_query import GetFileQuery
from src.storage.application.queries.get_file_query_handler import GetFileQueryHandler, FileQueryResult

# Infrastructure exports
from src.storage.infrastructure.dependencies_new import (
    get_storage_repository,
    get_file_validator,
    get_storage_factory_dep
)
from src.storage.infrastructure.factory import register_storage_provider

# Provider implementations
from src.storage.infrastructure.providers.local_provider import LocalStorageProvider, LocalStorageConfiguration
from src.storage.infrastructure.providers.s3_provider import S3StorageProvider, S3StorageConfiguration

__all__ = [
    # Domain
    "FileMetadata",
    "FilePath", 
    "FileSize",
    "StorageRepository",
    "StorageProvider",
    "StorageProviderFactory",
    "StorageConfiguration",
    
    # Application
    "UploadFileCommand",
    "UploadFileCommandHandler", 
    "GetFileQuery",
    "GetFileQueryHandler",
    "FileQueryResult",
    
    # Infrastructure
    "get_storage_repository",
    "get_file_validator",
    "get_storage_factory_dep",
    "register_storage_provider",
    
    # Providers
    "LocalStorageProvider",
    "LocalStorageConfiguration",
    "S3StorageProvider", 
    "S3StorageConfiguration",
]