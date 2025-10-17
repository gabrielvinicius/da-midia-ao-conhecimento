# src/storage/bootstrap.py
"""
Bootstrap module for storage services with SOLID principles.
"""
from typing import Dict, Any

# Infrastructure dependencies
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.infrastructure.cache import CacheService

# Storage services
from src.storage.application.storage_service import StorageService
from src.storage.infrastructure.dependencies import StorageServiceFactory

# Enhanced SOLID Services
from src.storage.application.services.storage_validator import StorageValidator
from src.storage.application.services.storage_metrics_service import StorageMetricsService
from src.storage.application.services.storage_state_manager import StorageStateManager
from src.storage.application.services.enhanced_storage_service import EnhancedStorageService

# Configuration
from src.storage.config.settings import StorageSettings


def bootstrap_storage_module(
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
    storage_provider: str = "local"
) -> Dict[str, Any]:
    """
    Constructs and returns the SOLID-enhanced services for the storage module.
    
    Args:
        metrics_collector: Metrics collection service
        cache_service: Cache service for state management
        storage_provider: Storage provider to use (local, s3, azure)
        
    Returns:
        Dict containing all storage services
    """
    
    # --- Infrastructure ---
    storage_settings = StorageSettings()
    storage_factory = StorageServiceFactory()
    base_storage_service = storage_factory.create_storage_service(storage_provider)
    
    # --- SOLID Services (Following SRP) ---
    storage_validator = StorageValidator(
        max_file_size=500 * 1024 * 1024,  # 500MB
        min_file_size=1  # 1 byte
    )
    
    storage_metrics_service = StorageMetricsService(
        metrics_collector=metrics_collector
    )
    
    storage_state_manager = StorageStateManager(
        cache_service=cache_service
    )
    
    # --- Enhanced Storage Service (SOLID compliant) ---
    enhanced_storage_service = EnhancedStorageService(
        storage_service=base_storage_service,
        validator=storage_validator,
        metrics_service=storage_metrics_service,
        state_manager=storage_state_manager
    )
    
    return {
        # Infrastructure
        "storage_settings": storage_settings,
        "storage_factory": storage_factory,
        
        # SOLID Services
        "storage_validator": storage_validator,
        "storage_metrics_service": storage_metrics_service,
        "storage_state_manager": storage_state_manager,
        "enhanced_storage_service": enhanced_storage_service,
        
        # Legacy Services (backward compatibility)
        "storage_service": base_storage_service,
    }