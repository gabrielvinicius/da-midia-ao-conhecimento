# src/providers/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers

from src.providers.domain.interfaces import IProviderRegistry
from src.providers.infrastructure.provider_registry import InMemoryProviderRegistry


class ProvidersContainer(containers.DeclarativeContainer):
    # Implementações concretas das interfaces de domínio
    provider_registry: providers.Provider[IProviderRegistry] = providers.Singleton(
        InMemoryProviderRegistry
    )


@dataclass
class ProvidersModule:
    provider_registry: IProviderRegistry


def build_providers_module() -> ProvidersModule:
    container = ProvidersContainer()
    return ProvidersModule(provider_registry=container.provider_registry())
