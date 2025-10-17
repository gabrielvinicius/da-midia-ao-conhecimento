# src/shared/domain/interfaces.py
"""
Domain interfaces for shared module following DIP principle.
All high-level modules depend on these abstractions, not concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import UUID


class CacheService(ABC):
    """Interface for caching services."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, expiration: int = None) -> bool:
        """Set value in cache with optional expiration."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class FileService(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    async def read_file(self, file_path: str) -> bytes:
        """Read file contents."""
        pass
    
    @abstractmethod
    async def write_file(self, file_path: str, content: bytes) -> bool:
        """Write content to file."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file."""
        pass
    
    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass


class IdService(ABC):
    """Interface for ID generation services."""
    
    @abstractmethod
    def generate_uuid(self) -> UUID:
        """Generate a new UUID."""
        pass
    
    @abstractmethod
    def generate_short_id(self, length: int = 8) -> str:
        """Generate a short alphanumeric ID."""
        pass
    
    @abstractmethod
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        pass


class PasswordService(ABC):
    """Interface for password operations."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        pass
    
    @abstractmethod
    def generate_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        pass


class ValidationService(ABC):
    """Interface for validation services."""
    
    @abstractmethod
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pass
    
    @abstractmethod
    def validate_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate data against schema, return errors."""
        pass
    
    @abstractmethod
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input."""
        pass


class EventPublisher(ABC):
    """Interface for event publishing."""
    
    @abstractmethod
    async def publish(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Publish an event."""
        pass


class SubscriptionManager(ABC):
    """Interface for event subscription management."""
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: callable) -> str:
        """Subscribe to an event type, return subscription ID."""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from event."""
        pass
    
    @abstractmethod
    def get_handlers(self, event_type: str) -> List[callable]:
        """Get handlers for event type."""
        pass


class MetricsCollector(ABC):
    """Interface for metrics collection."""
    
    @abstractmethod
    async def record_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Record counter metric."""
        pass
    
    @abstractmethod
    async def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record gauge metric."""
        pass
    
    @abstractmethod
    async def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record histogram metric."""
        pass


class CircuitBreakerService(ABC):
    """Interface for circuit breaker functionality."""
    
    @abstractmethod
    async def call(self, func: callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        pass
    
    @abstractmethod
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset circuit breaker to closed state."""
        pass