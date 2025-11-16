# src/providers/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers

from src.providers.domain.interfaces import (
    IProviderRegistry,
    ProviderCapability,
    ProviderStatus,
    ProviderType,
)
from src.providers.domain.provider import Provider
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
    provider_registry = container.provider_registry()
    _seed_default_providers(provider_registry)
    return ProvidersModule(provider_registry=provider_registry)


def _seed_default_providers(registry: IProviderRegistry) -> None:
    """Register built-in providers so the API returns meaningful data."""
    defaults = [
        Provider(
            name="local",
            provider_type=ProviderType.STORAGE,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.READ,
                ProviderCapability.WRITE,
                ProviderCapability.DELETE,
                ProviderCapability.LIST,
            ],
            configuration={"type": "local"},
        ),
        Provider(
            name="s3",
            provider_type=ProviderType.STORAGE,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.READ,
                ProviderCapability.WRITE,
                ProviderCapability.DELETE,
                ProviderCapability.LIST,
                ProviderCapability.VERSIONING,
                ProviderCapability.ENCRYPTION,
            ],
            configuration={"type": "s3"},
        ),
        Provider(
            name="minio",
            provider_type=ProviderType.STORAGE,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.READ,
                ProviderCapability.WRITE,
                ProviderCapability.DELETE,
                ProviderCapability.LIST,
                ProviderCapability.ENCRYPTION,
            ],
            configuration={"type": "minio"},
        ),
        Provider(
            name="fastwhisper",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.REAL_TIME,
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="whisper",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="huggingface",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
                ProviderCapability.CUSTOM_MODELS,
            ],
        ),
        Provider(
            name="builtin",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="openai",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="huggingface",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
                ProviderCapability.CUSTOM_MODELS,
            ],
        ),
    ]

    for provider in defaults:
        # InMemoryProviderRegistry already guards against duplicates; we ignore warnings.
        registry.register_provider(provider)
