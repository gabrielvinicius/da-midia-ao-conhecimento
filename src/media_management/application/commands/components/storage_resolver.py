"""Storage resolver collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class StorageServiceResolver(Protocol):
    """Resolves storage service implementations based on provider."""

    def resolve(self, storage_provider: str) -> Any:
        """Return the storage service for the given provider."""


@dataclass
class DefaultStorageServiceResolver(StorageServiceResolver):
    """Default resolver that supports callables or factory objects."""

    factory: Any

    def resolve(self, storage_provider: str) -> Any:
        factory = self.factory

        if callable(factory) and not hasattr(factory, "create_storage_service"):
            return factory(storage_provider)

        if hasattr(factory, "create_storage_service"):
            return factory.create_storage_service(storage_provider)

        raise ValueError("Invalid storage service factory provided")
