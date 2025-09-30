# src/sentiment_analysis/infrastructure/dependencies.py
from typing import Dict, Type, List, Callable
import importlib
import pkgutil
import pathlib

from .interfaces import ISentimentAnalysisService

# Service registry
_sentiment_registry: Dict[str, Type[ISentimentAnalysisService]] = {}
_plugins_loaded = False

# Type alias for the factory
SentimentServiceFactory = Callable[[str], ISentimentAnalysisService]

def register_sentiment_analysis(provider: str):
    """A decorator to register sentiment analysis provider classes."""
    def decorator(cls: Type[ISentimentAnalysisService]):
        _sentiment_registry[provider] = cls
        return cls
    return decorator

def get_available_sentiment_providers() -> List[str]:
    """Returns a list of all registered sentiment provider names."""
    _load_plugins()
    return list(_sentiment_registry.keys())

def create_sentiment_analysis_service(provider: str) -> ISentimentAnalysisService:
    """Factory function to create a service instance by name."""
    _load_plugins()
    if provider not in _sentiment_registry:
        raise ValueError(f"Sentiment analysis provider '{provider}' is not registered")
    return _sentiment_registry[provider]()

def get_sentiment_service_factory() -> SentimentServiceFactory:
    """Dependency provider that returns the factory function itself."""
    return create_sentiment_analysis_service

def _load_plugins():
    """Dynamically loads all providers in this directory."""
    global _plugins_loaded
    if _plugins_loaded:
        return

    package_path = pathlib.Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        if not module_name.startswith("__") and module_name != "dependencies":
            importlib.import_module(f".{module_name}", package=__name__.rsplit(".", 1)[0])
    _plugins_loaded = True
