"""Provider module API dependencies."""
from typing import Annotated

from fastapi import Depends

from src.providers.domain.interfaces import IProviderRegistry


class ProviderDependenciesNotConfigured(RuntimeError):
    pass


def get_provider_registry() -> IProviderRegistry:
    raise ProviderDependenciesNotConfigured(
        "Provider registry dependency not configured. Register providers in the lifespan handler."
    )


ProviderRegistryDep = Annotated[IProviderRegistry, Depends(get_provider_registry)]


__all__ = [
    "ProviderDependenciesNotConfigured",
    "ProviderRegistryDep",
    "get_provider_registry",
]
