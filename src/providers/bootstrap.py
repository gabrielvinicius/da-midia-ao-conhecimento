# src/providers/bootstrap.py
from dataclasses import dataclass

from fastapi import FastAPI

from src.providers.api.dependencies import get_provider_registry
from src.providers.domain.interfaces import (
    IProviderRegistry,
    ProviderCapability,
    ProviderStatus,
    ProviderType,
)
from src.providers.domain.provider import Provider
from src.providers.domain.provider_metadata import get_provider_metadata
from src.providers.infrastructure.provider_registry import InMemoryProviderRegistry


@dataclass
class ProvidersModule:
    provider_registry: IProviderRegistry


def build_providers_module() -> ProvidersModule:
    provider_registry = InMemoryProviderRegistry()
    _seed_default_providers(provider_registry)
    return ProvidersModule(provider_registry=provider_registry)


def bind_providers_module(app: FastAPI, module: ProvidersModule) -> None:
    """Expose the provider registry through FastAPI dependency overrides."""

    app.dependency_overrides[get_provider_registry] = lambda: module.provider_registry


def _seed_default_providers(registry: IProviderRegistry) -> None:
    """Register built-in providers so the API returns meaningful data.

    Canonical provider names (usar em UI/API):
    - storage: local, s3, minio
    - transcription: fastwhisper, whisper, huggingface
    - summarization: builtin, openai, huggingface
    - sentiment: transformers, vader
    - topic_modeling: bertopic
    """

    def _with_metadata(provider: Provider) -> Provider:
        metadata = get_provider_metadata(provider.provider_type, provider.name)
        if metadata:
            provider.display_name = metadata.label
            provider.description = metadata.description
        return provider

    defaults = [
        _with_metadata(Provider(
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
        )),
        _with_metadata(Provider(
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
        )),
        _with_metadata(Provider(
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
        )),
        _with_metadata(Provider(
            name="fastwhisper",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.REAL_TIME,
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
            configuration={"adapter": "fastwhisper"},
        )),
        _with_metadata(Provider(
            name="whisper",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        )),
        _with_metadata(Provider(
            name="huggingface",
            provider_type=ProviderType.TRANSCRIPTION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
                ProviderCapability.CUSTOM_MODELS,
            ],
        )),
        _with_metadata(Provider(
            name="builtin",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        )),
        _with_metadata(Provider(
            name="openai",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        )),
        _with_metadata(Provider(
            name="huggingface",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
                ProviderCapability.CUSTOM_MODELS,
            ],
        )),
        _with_metadata(Provider(
            name="transformers",
            provider_type=ProviderType.SENTIMENT_ANALYSIS,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        )),
        _with_metadata(Provider(
            name="vader",
            provider_type=ProviderType.SENTIMENT_ANALYSIS,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
            ],
        )),
        _with_metadata(Provider(
            name="bertopic",
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
            ],
        )),
    ]

    for provider in defaults:
        # InMemoryProviderRegistry already guards against duplicates; we ignore warnings.
        registry.register_provider(provider)


__all__ = [
    "ProvidersModule",
    "bind_providers_module",
    "build_providers_module",
]
