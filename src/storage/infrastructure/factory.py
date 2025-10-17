# src/storage/infrastructure/factory.py
"""
Storage provider factory implementation - DIP and OCP compliance.
"""
from typing import Dict, Type, Callable
from src.storage.domain.interfaces import StorageProviderFactory, StorageProvider, StorageConfiguration
from src.storage.infrastructure.providers.local_provider import LocalStorageProvider, LocalStorageConfiguration
from src.storage.infrastructure.providers.s3_provider import S3StorageProvider, S3StorageConfiguration


class ConcreteStorageProviderFactory(StorageProviderFactory):
    """
    Concrete factory for creating storage providers.
    Follows OCP - new providers can be added without modifying existing code.
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[StorageProvider]] = {}
        self._config_factories: Dict[str, Callable[..., StorageConfiguration]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default storage providers."""
        self.register_provider(
            "local", 
            LocalStorageProvider,
            LocalStorageConfiguration
        )
        self.register_provider(
            "s3", 
            S3StorageProvider,
            S3StorageConfiguration
        )
    
    def register_provider(
        self, 
        provider_type: str, 
        provider_class: Type[StorageProvider],
        config_class: Type[StorageConfiguration]
    ) -> None:
        """
        Register a new storage provider.
        Enables extension without modification (OCP).
        """
        self._providers[provider_type] = provider_class
        self._config_factories[provider_type] = config_class
    
    def create_provider(self, provider_type: str, config: StorageConfiguration) -> StorageProvider:
        """Create storage provider instance."""
        if provider_type not in self._providers:
            raise ValueError(f"Unknown storage provider: {provider_type}")
        
        provider_class = self._providers[provider_type]
        return provider_class(config)
    
    def create_provider_with_params(self, provider_type: str, **config_params) -> StorageProvider:
        """Create provider with configuration parameters."""
        if provider_type not in self._config_factories:
            raise ValueError(f"Unknown storage provider: {provider_type}")
        
        config_class = self._config_factories[provider_type]
        config = config_class(**config_params)
        return self.create_provider(provider_type, config)
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        return list(self._providers.keys())


# Global factory instance
_storage_factory = ConcreteStorageProviderFactory()


def get_storage_factory() -> StorageProviderFactory:
    """Get the global storage factory instance."""
    return _storage_factory


def register_storage_provider(
    provider_type: str, 
    provider_class: Type[StorageProvider],
    config_class: Type[StorageConfiguration]
) -> None:
    """
    Register a custom storage provider globally.
    Allows third-party extensions (OCP).
    """
    _storage_factory.register_provider(provider_type, provider_class, config_class)