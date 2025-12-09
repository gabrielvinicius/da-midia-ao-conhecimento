# src/providers/infrastructure/provider_registry.py
from collections import defaultdict
from typing import Dict, List, Optional

import structlog

from src.providers.domain.interfaces import (
    IProvider,
    IProviderRegistry,
    ProviderCapability,
    ProviderStatus,
    ProviderType,
)
from src.providers.domain.provider import Provider  # Para a entidade Provider

logger = structlog.get_logger(__name__)


class InMemoryProviderRegistry(IProviderRegistry):
    """In-memory implementation of IProviderRegistry for managing providers."""

    def __init__(self):
        self._providers: Dict[ProviderType, Dict[str, Provider]] = defaultdict(dict)

    def register_provider(self, provider: IProvider) -> None:
        if not isinstance(provider, Provider):
            raise TypeError("Only instances of Provider can be registered.")

        provider_type = provider.get_type()
        provider_name = provider.get_name()

        if provider_name in self._providers[provider_type]:
            logger.warning(
                "provider_registry.provider_already_registered",
                provider_name=provider_name,
                provider_type=provider_type.value
            )
            # Poderia levantar uma exceção ou atualizar o provedor existente
            return

        self._providers[provider_type][provider_name] = provider
        logger.info(
            "provider_registry.provider_registered",
            provider_name=provider_name,
            provider_type=provider_type.value
        )

    def unregister_provider(self, name: str, provider_type: ProviderType) -> bool:
        if name in self._providers[provider_type]:
            del self._providers[provider_type][name]
            logger.info(
                "provider_registry.provider_unregistered",
                provider_name=name,
                provider_type=provider_type.value
            )
            return True
        logger.warning(
            "provider_registry.provider_not_found_for_unregister",
            provider_name=name,
            provider_type=provider_type.value
        )
        return False

    def get_provider(self, name: str, provider_type: ProviderType) -> Optional[IProvider]:
        return self._providers[provider_type].get(name)

    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        if provider_type:
            return list(self._providers[provider_type].values())

        all_providers = []
        for type_providers in self._providers.values():
            all_providers.extend(type_providers.values())
        return all_providers

    def get_providers_by_capability(self, capability: ProviderCapability) -> List[IProvider]:
        matching_providers = []
        for provider_type_dict in self._providers.values():
            for provider in provider_type_dict.values():
                if capability in provider.get_capabilities():
                    matching_providers.append(provider)
        return matching_providers

    def get_active_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        active_providers = []
        providers_to_check = self.list_providers(provider_type)
        for provider in providers_to_check:
            if provider.status == ProviderStatus.ACTIVE: # Acessar diretamente o status da entidade Provider
                active_providers.append(provider)
        return active_providers
