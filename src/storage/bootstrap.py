"""Bootstrap module for storage services."""
from typing import Any, Dict

from src.shared.infrastructure.cache import CacheService
from src.shared.monitoring.metrics_collector import MetricsCollector

from src.storage.application.services.storage_service import StorageService
from src.storage.infrastructure.local_storage_service import LocalStorageService


def bootstrap_storage_module(
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
    storage_provider: str = "local"
) -> Dict[str, Any]:
    """Constructs and returns the services for the storage module.
    
    Args:
        metrics_collector: Metrics collection service
        cache_service: Cache service
        storage_provider: Storage provider to use (local is default)
        
    Returns:
        Dict containing storage services
    """
    # Infrastructure (Repository)
    if storage_provider == "local":
        repository = LocalStorageService(root_directory="storage")
    else:
        # Fallback or support for S3 if implemented
        # For now defaulting to local to ensure stability
        repository = LocalStorageService(root_directory="storage")

    # Application Service
    storage_service = StorageService(repository=repository)

    return {
        "storage_service": storage_service,
        "repository": repository,
    }