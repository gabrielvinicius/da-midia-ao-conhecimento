"""
Simplified dependency injection - replacing complex factory pattern
"""
from typing import Dict, Any, Callable, TypeVar, Type
import inspect

T = TypeVar('T')

class SimpleContainer:
    """Simple DI container replacing multiple factories"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
    
    def register(self, interface: Type[T], implementation: T):
        """Register a service instance"""
        self._services[interface.__name__] = implementation
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T]):
        """Register a factory function"""
        self._factories[interface.__name__] = factory
    
    def get(self, interface: Type[T]) -> T:
        """Get service instance"""
        name = interface.__name__
        
        if name in self._services:
            return self._services[name]
        
        if name in self._factories:
            instance = self._factories[name]()
            self._services[name] = instance  # Cache it
            return instance
        
        raise ValueError(f"Service {name} not registered")

# Global container instance
container = SimpleContainer()