# src/storage/infrastructure/dependencies_new.py
"""
Dependency injection setup for storage module - DIP compliance.
"""
import os
from typing import Optional

from src.storage.domain.interfaces import (
    StorageRepository, 
    StorageProviderFactory,
    StorageOperationLogger,
    StorageMetrics
)
from src.storage.domain.services.file_validator import DefaultFileValidator, FileValidator
from src.storage.domain.services.storage_coordinator import StorageCoordinator
from src.storage.application.storage_repository_impl import StorageRepositoryImpl
from src.storage.infrastructure.factory import get_storage_factory
from src.storage.infrastructure.logging import StructuredStorageLogger, NoOpStorageLogger
from src.storage.infrastructure.metrics import PrometheusStorageMetrics, NoOpStorageMetrics
from src.storage.infrastructure.providers.local_provider import LocalStorageConfiguration
from src.storage.infrastructure.providers.s3_provider import S3StorageConfiguration


class StorageDependencyContainer:
    """
    Dependency injection container for storage module.
    Follows DIP by managing dependencies through abstractions.
    """
    
    def __init__(self):
        self._factory: Optional[StorageProviderFactory] = None
        self._logger: Optional[StorageOperationLogger] = None
        self._metrics: Optional[StorageMetrics] = None
        self._validator: Optional[FileValidator] = None
        self._repository: Optional[StorageRepository] = None
    
    def get_storage_factory(self) -> StorageProviderFactory:
        """Get storage provider factory."""
        if self._factory is None:
            self._factory = get_storage_factory()
        return self._factory
    
    def get_storage_logger(self) -> StorageOperationLogger:
        """Get storage operation logger."""
        if self._logger is None:
            if os.getenv("ENABLE_STORAGE_LOGGING", "true").lower() == "true":
                self._logger = StructuredStorageLogger()
            else:
                self._logger = NoOpStorageLogger()
        return self._logger
    
    def get_storage_metrics(self) -> StorageMetrics:
        """Get storage metrics collector."""
        if self._metrics is None:
            if os.getenv("ENABLE_STORAGE_METRICS", "true").lower() == "true":
                self._metrics = PrometheusStorageMetrics()
            else:
                self._metrics = NoOpStorageMetrics()
        return self._metrics
    
    def get_file_validator(self) -> FileValidator:
        """Get file validator."""
        if self._validator is None:
            max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
            self._validator = DefaultFileValidator(max_size_mb=max_size_mb)
        return self._validator
    
    def get_storage_repository(self) -> StorageRepository:
        """Get high-level storage repository."""
        if self._repository is None:
            # Create provider
            provider_type = os.getenv("STORAGE_PROVIDER", "local")
            provider = self._create_provider(provider_type)
            
            # Create coordinator
            coordinator = StorageCoordinator(
                provider=provider,
                logger=self.get_storage_logger(),
                metrics=self.get_storage_metrics()
            )
            
            # Create repository
            self._repository = StorageRepositoryImpl(
                storage_coordinator=coordinator,
                file_validator=self.get_file_validator()
            )
        
        return self._repository
    
    def _create_provider(self, provider_type: str):
        """Create storage provider based on type."""
        factory = self.get_storage_factory()
        
        if provider_type == "local":
            config = LocalStorageConfiguration(
                root_path=os.getenv("LOCAL_STORAGE_ROOT", "storage")
            )
        elif provider_type == "s3":
            config = S3StorageConfiguration(
                bucket_name=os.getenv("BUCKET_NAME", ""),
                endpoint_url=os.getenv("ENDPOINT_URL", ""),
                access_key=os.getenv("ACCESS_KEY", ""),
                secret_key=os.getenv("SECRET_KEY_S3", ""),
                region=os.getenv("AWS_REGION", "us-east-1")
            )
        else:
            raise ValueError(f"Unknown storage provider: {provider_type}")
        
        return factory.create_provider(provider_type, config)


# Global container instance
_container = StorageDependencyContainer()


def get_storage_repository() -> StorageRepository:
    """Dependency provider for storage repository."""
    return _container.get_storage_repository()


def get_file_validator() -> FileValidator:
    """Dependency provider for file validator."""
    return _container.get_file_validator()


def get_storage_factory_dep() -> StorageProviderFactory:
    """Dependency provider for storage factory."""
    return _container.get_storage_factory()