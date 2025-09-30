# src/topic_modeling/infrastructure/dependencies.py
from typing import Dict, Type, List, Callable
import importlib
import pkgutil
import pathlib

from .interfaces import ITopicModelingService

# Service registry
_topic_registry: Dict[str, Type[ITopicModelingService]] = {}
_plugins_loaded = False

# Type alias for the factory
TopicServiceFactory = Callable[[str], ITopicModelingService]

def register_topic_modeling(provider: str):
    """A decorator to register topic modeling provider classes."""
    def decorator(cls: Type[ITopicModelingService]):
        _topic_registry[provider] = cls
        return cls
    return decorator

def get_available_topic_providers() -> List[str]:
    """Returns a list of all registered topic modeling provider names."""
    _load_plugins()
    return list(_topic_registry.keys())

def create_topic_modeling_service(provider: str) -> ITopicModelingService:
    """Factory function to create a service instance by name."""
    _load_plugins()
    if provider not in _topic_registry:
        raise ValueError(f"Topic modeling provider '{provider}' is not registered")
    return _topic_registry[provider]()

def get_topic_service_factory() -> TopicServiceFactory:
    """Dependency provider that returns the factory function itself."""
    return create_topic_modeling_service

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
