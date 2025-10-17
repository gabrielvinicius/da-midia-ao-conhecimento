# src/topic_modeling/infrastructure/factory.py
"""
Topic modeling provider factory implementation - DIP and OCP compliance.
"""
from typing import Dict, Type, Callable
from src.topic_modeling.domain.interfaces import (
    TopicModelingProviderFactory, 
    TopicModelingProvider, 
    TopicModelingConfiguration
)
from src.topic_modeling.infrastructure.providers.sklearn_provider import (
    SklearnTopicModelingProvider, 
    SklearnConfiguration
)
from src.topic_modeling.infrastructure.providers.gensim_provider import (
    GensimTopicModelingProvider, 
    GensimConfiguration
)


class ConcreteTopicModelingProviderFactory(TopicModelingProviderFactory):
    """
    Concrete factory for creating topic modeling providers.
    Follows OCP - new providers can be added without modifying existing code.
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[TopicModelingProvider]] = {}
        self._config_factories: Dict[str, Callable[..., TopicModelingConfiguration]] = {}
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default topic modeling providers."""
        self.register_provider(
            "sklearn_lda", 
            SklearnTopicModelingProvider,
            lambda **kwargs: SklearnConfiguration(algorithm="lda", **kwargs)
        )
        self.register_provider(
            "sklearn_nmf", 
            SklearnTopicModelingProvider,
            lambda **kwargs: SklearnConfiguration(algorithm="nmf", **kwargs)
        )
        self.register_provider(
            "sklearn_kmeans", 
            SklearnTopicModelingProvider,
            lambda **kwargs: SklearnConfiguration(algorithm="kmeans", **kwargs)
        )
        
        # Try to register Gensim providers if available
        try:
            self.register_provider(
                "gensim_lda", 
                GensimTopicModelingProvider,
                lambda **kwargs: GensimConfiguration(algorithm="lda", **kwargs)
            )
            self.register_provider(
                "gensim_lsi", 
                GensimTopicModelingProvider,
                lambda **kwargs: GensimConfiguration(algorithm="lsi", **kwargs)
            )
            self.register_provider(
                "gensim_hdp", 
                GensimTopicModelingProvider,
                lambda **kwargs: GensimConfiguration(algorithm="hdp", **kwargs)
            )
        except Exception:
            # Gensim not available, skip registration
            pass
    
    def register_provider(
        self, 
        provider_type: str, 
        provider_class: Type[TopicModelingProvider],
        config_factory: Callable[..., TopicModelingConfiguration]
    ) -> None:
        """
        Register a new topic modeling provider.
        Enables extension without modification (OCP).
        """
        self._providers[provider_type] = provider_class
        self._config_factories[provider_type] = config_factory
    
    def create_provider(
        self, 
        provider_type: str, 
        config: TopicModelingConfiguration
    ) -> TopicModelingProvider:
        """Create topic modeling provider instance."""
        if provider_type not in self._providers:
            raise ValueError(f"Unknown topic modeling provider: {provider_type}")
        
        provider_class = self._providers[provider_type]
        return provider_class(config)
    
    def create_provider_with_params(
        self, 
        provider_type: str, 
        **config_params
    ) -> TopicModelingProvider:
        """Create provider with configuration parameters."""
        if provider_type not in self._config_factories:
            raise ValueError(f"Unknown topic modeling provider: {provider_type}")
        
        config_factory = self._config_factories[provider_type]
        config = config_factory(**config_params)
        return self.create_provider(provider_type, config)
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        return list(self._providers.keys())
    
    def get_providers_by_algorithm(self, algorithm: str) -> list[str]:
        """Get providers that support a specific algorithm."""
        matching_providers = []
        for provider_type in self._providers.keys():
            if algorithm.lower() in provider_type.lower():
                matching_providers.append(provider_type)
        return matching_providers


# Global factory instance
_topic_modeling_factory = ConcreteTopicModelingProviderFactory()


def get_topic_modeling_factory() -> TopicModelingProviderFactory:
    """Get the global topic modeling factory instance."""
    return _topic_modeling_factory


def register_topic_modeling_provider(
    provider_type: str, 
    provider_class: Type[TopicModelingProvider],
    config_factory: Callable[..., TopicModelingConfiguration]
) -> None:
    """
    Register a custom topic modeling provider globally.
    Allows third-party extensions (OCP).
    """
    _topic_modeling_factory.register_provider(provider_type, provider_class, config_factory)