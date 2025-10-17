# src/summarization/infrastructure/factory.py
"""
Summarization provider factory implementation - DIP and OCP compliance.
"""
from typing import Dict, Type, Callable
from src.summarization.domain.interfaces import SummaryProviderFactory, SummaryProvider, SummaryConfiguration
from src.summarization.infrastructure.providers.huggingface_provider import (
    HuggingFaceSummaryProvider, 
    HuggingFaceConfiguration
)
from src.summarization.infrastructure.providers.openai_provider import (
    OpenAISummaryProvider, 
    OpenAIConfiguration
)


class ConcreteSummaryProviderFactory(SummaryProviderFactory):
    """
    Concrete factory for creating summarization providers.
    Follows OCP - new providers can be added without modifying existing code.
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[SummaryProvider]] = {}
        self._config_factories: Dict[str, Callable[..., SummaryConfiguration]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default summarization providers."""
        self.register_provider(
            "huggingface", 
            HuggingFaceSummaryProvider,
            HuggingFaceConfiguration
        )
        self.register_provider(
            "openai", 
            OpenAISummaryProvider,
            OpenAIConfiguration
        )
    
    def register_provider(
        self, 
        provider_type: str, 
        provider_class: Type[SummaryProvider],
        config_class: Type[SummaryConfiguration]
    ) -> None:
        """
        Register a new summarization provider.
        Enables extension without modification (OCP).
        """
        self._providers[provider_type] = provider_class
        self._config_factories[provider_type] = config_class
    
    def create_provider(self, provider_type: str, config: SummaryConfiguration) -> SummaryProvider:
        """Create summarization provider instance."""
        if provider_type not in self._providers:
            raise ValueError(f"Unknown summarization provider: {provider_type}")
        
        provider_class = self._providers[provider_type]
        return provider_class(config)
    
    def create_provider_with_params(self, provider_type: str, **config_params) -> SummaryProvider:
        """Create provider with configuration parameters."""
        if provider_type not in self._config_factories:
            raise ValueError(f"Unknown summarization provider: {provider_type}")
        
        config_class = self._config_factories[provider_type]
        config = config_class(**config_params)
        return self.create_provider(provider_type, config)
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        return list(self._providers.keys())


# Global factory instance
_summary_factory = ConcreteSummaryProviderFactory()


def get_summary_factory() -> SummaryProviderFactory:
    """Get the global summarization factory instance."""
    return _summary_factory


def register_summary_provider(
    provider_type: str, 
    provider_class: Type[SummaryProvider],
    config_class: Type[SummaryConfiguration]
) -> None:
    """
    Register a custom summarization provider globally.
    Allows third-party extensions (OCP).
    """
    _summary_factory.register_provider(provider_type, provider_class, config_class)