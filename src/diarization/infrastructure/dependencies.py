# src/diarization/infrastructure/dependencies.py
from typing import Dict, Type, List, Callable
import importlib
import pkgutil
import pathlib

from .interfaces import IDiarizationService

# Service registry
_diarization_registry: Dict[str, Type[IDiarizationService]] = {}
_plugins_loaded = False

# Type alias for the factory
DiarizationServiceFactory = Callable[[str], IDiarizationService]

def register_diarization(provider: str):
    """A decorator to register diarization provider classes."""
    def decorator(cls: Type[IDiarizationService]):
        _diarization_registry[provider] = cls
        return cls
    return decorator

def get_available_diarization_providers() -> List[str]:
    """Returns a list of all registered diarization provider names."""
    _load_diarization_plugins()
    return list(_diarization_registry.keys())

def create_diarization_service(provider: str) -> IDiarizationService:
    """Factory function to create a diarization service instance by name."""
    _load_diarization_plugins()
    if provider not in _diarization_registry:
        raise ValueError(f"Diarization provider '{provider}' is not registered")
    return _diarization_registry[provider]()

def get_diarization_service_factory() -> DiarizationServiceFactory:
    """Dependency provider that returns the factory function itself."""
    return create_diarization_service

def _load_diarization_plugins():
    """Dynamically loads all diarization providers in this directory."""
    global _plugins_loaded
    if _plugins_loaded:
        return

    package_path = pathlib.Path(__file__).parent
    package_name = __name__.rsplit(".", 1)[0]

    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        if module_name.startswith("_") or module_name in ["dependencies", "interfaces"]:
            continue
        full_module_name = f"{package_name}.{module_name}"
        importlib.import_module(full_module_name)

    _plugins_loaded = True
