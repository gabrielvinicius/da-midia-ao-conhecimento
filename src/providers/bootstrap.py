# src/providers/bootstrap.py
from dependency_injector import containers, providers
from typing import Dict, Any

from src.providers.domain.interfaces import IProviderRegistry
from src.providers.infrastructure.provider_registry import InMemoryProviderRegistry

class ProvidersContainer(containers.DeclarativeContainer):
    # Implementações concretas das interfaces de domínio
    provider_registry: providers.Provider[IProviderRegistry] = providers.Singleton(
        InMemoryProviderRegistry
    )

    # Se houver outros serviços de aplicação ou handlers, eles seriam registrados aqui.
    # Ex:
    # provider_service: providers.Provider[ProviderService] = providers.Factory(
    #     ProviderService,
    #     provider_registry=provider_registry
    # )
