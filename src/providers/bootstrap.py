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
        Provider(
            name="transformers",
            provider_type=ProviderType.SENTIMENT_ANALYSIS,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="vader",
            provider_type=ProviderType.SENTIMENT_ANALYSIS,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
            ],
        ),
        Provider(
            name="sklearn_lda",
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
            ],
            configuration={"algorithm": "LatentDirichletAllocation"},
        ),
        Provider(
            name="bertopic",
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
                ProviderCapability.MULTI_LANGUAGE,
            ],
        ),
        Provider(
            name="keyword_frequency",
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=[
                ProviderCapability.BATCH_PROCESSING,
            ],
            configuration={"strategy": "tfidf"},
        ),
    ]

    for provider in defaults:
        # InMemoryProviderRegistry already guards against duplicates; we ignore warnings.
        registry.register_provider(provider)


__all__ = [
    "ProvidersModule",
    "bind_providers_module",
    "build_providers_module",
]
