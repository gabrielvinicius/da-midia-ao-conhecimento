"""Helpers de bootstrap/DI do contexto de storage.

Mantém a API pública `src.storage.infrastructure.dependencies.*` estável,
enquanto a implementação fica organizada em submódulos (ex.: providers).
"""

from .providers import StorageServiceFactory, get_storage_service_factory

__all__ = [
    "StorageServiceFactory",
    "get_storage_service_factory",
]

