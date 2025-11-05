# src/providers/domain/interfaces.py
"""Domain interfaces for providers module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderType(Enum):
    """Types of providers in the system."""

    STORAGE = "storage"
    TRANSCRIPTION = "transcription"
    SUMMARIZATION = "summarization"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOPIC_MODELING = "topic_modeling"
    EMAIL = "email"
    SMS = "sms"
    PUSH_NOTIFICATION = "push_notification"
    AI_MODEL = "ai_model"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"


class ProviderStatus(Enum):
    """Status of providers."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ProviderCapability(Enum):
    """Capabilities that providers can support."""

    # Storage capabilities
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    LIST = "list"
    VERSIONING = "versioning"
    ENCRYPTION = "encryption"

    # AI/ML capabilities
    REAL_TIME = "real_time"
    BATCH_PROCESSING = "batch_processing"
    STREAMING = "streaming"
    MULTI_LANGUAGE = "multi_language"
    CUSTOM_MODELS = "custom_models"

    # Communication capabilities
    TEMPLATES = "templates"
    SCHEDULING = "scheduling"
    TRACKING = "tracking"
    WEBHOOKS = "webhooks"


class IProvider(ABC):
    """Base interface for all providers."""

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass

    @abstractmethod
    def get_type(self) -> ProviderType:
        """Get provider type."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Get provider version."""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        """Get provider capabilities."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        pass

    @abstractmethod
    def get_configuration(self) -> Dict[str, Any]:
        """Get provider configuration."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize provider with configuration."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        pass


class IProviderRegistry(ABC):
    """Interface for provider registry operations."""

    @abstractmethod
    def register_provider(self, provider: IProvider) -> None:
        """Register a provider."""
        pass

    @abstractmethod
    def unregister_provider(self, name: str, provider_type: ProviderType) -> bool:
        """Unregister a provider."""
        pass

    @abstractmethod
    def get_provider(self, name: str, provider_type: ProviderType) -> Optional[IProvider]:
        """Get a specific provider."""
        pass

    @abstractmethod
    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        """List providers by type."""
        pass

    @abstractmethod
    def get_providers_by_capability(self, capability: ProviderCapability) -> List[IProvider]:
        """Get providers that support specific capability."""
        pass

    @abstractmethod
    def get_active_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        """Get active providers."""
        pass
