"""
Domain interfaces for providers module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from uuid import UUID
from enum import Enum
from datetime import datetime


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


class IProviderHealthChecker(ABC):
    """Interface for provider health checking operations."""
    
    @abstractmethod
    async def check_provider_health(self, provider: IProvider) -> Dict[str, Any]:
        """Check health of a specific provider."""
        pass
    
    @abstractmethod
    async def check_all_providers_health(self, provider_type: Optional[ProviderType] = None) -> Dict[str, Dict[str, Any]]:
        """Check health of all providers."""
        pass
    
    @abstractmethod
    async def get_provider_metrics(self, provider_name: str, provider_type: ProviderType) -> Dict[str, Any]:
        """Get metrics for a specific provider."""
        pass
    
    @abstractmethod
    async def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        pass


class IProviderSelector(ABC):
    """Interface for provider selection operations."""
    
    @abstractmethod
    async def select_best_provider(
        self,
        provider_type: ProviderType,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[IProvider]:
        """Select the best provider based on criteria."""
        pass
    
    @abstractmethod
    async def select_providers_for_load_balancing(
        self,
        provider_type: ProviderType,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        count: int = 2
    ) -> List[IProvider]:
        """Select multiple providers for load balancing."""
        pass
    
    @abstractmethod
    async def get_fallback_provider(
        self,
        primary_provider: IProvider,
        required_capabilities: Optional[List[ProviderCapability]] = None
    ) -> Optional[IProvider]:
        """Get fallback provider for primary provider."""
        pass


class IProviderConfiguration(ABC):
    """Interface for provider configuration management."""
    
    @abstractmethod
    async def get_provider_config(self, provider_name: str, provider_type: ProviderType) -> Dict[str, Any]:
        """Get configuration for a provider."""
        pass
    
    @abstractmethod
    async def update_provider_config(
        self,
        provider_name: str,
        provider_type: ProviderType,
        config: Dict[str, Any]
    ) -> bool:
        """Update provider configuration."""
        pass
    
    @abstractmethod
    async def validate_provider_config(
        self,
        provider_name: str,
        provider_type: ProviderType,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate provider configuration."""
        pass
    
    @abstractmethod
    async def get_default_config(self, provider_name: str, provider_type: ProviderType) -> Dict[str, Any]:
        """Get default configuration for a provider."""
        pass


class IProviderMetrics(ABC):
    """Interface for provider metrics operations."""
    
    @abstractmethod
    async def record_provider_usage(
        self,
        provider_name: str,
        provider_type: ProviderType,
        operation: str,
        duration: float,
        success: bool
    ) -> None:
        """Record provider usage metrics."""
        pass
    
    @abstractmethod
    async def get_provider_performance_metrics(
        self,
        provider_name: str,
        provider_type: ProviderType
    ) -> Dict[str, Any]:
        """Get performance metrics for a provider."""
        pass
    
    @abstractmethod
    async def get_provider_reliability_metrics(
        self,
        provider_name: str,
        provider_type: ProviderType
    ) -> Dict[str, Any]:
        """Get reliability metrics for a provider."""
        pass
    
    @abstractmethod
    async def get_cost_metrics(
        self,
        provider_name: str,
        provider_type: ProviderType
    ) -> Dict[str, Any]:
        """Get cost metrics for a provider."""
        pass


class IProviderLoadBalancer(ABC):
    """Interface for provider load balancing operations."""
    
    @abstractmethod
    async def distribute_request(
        self,
        provider_type: ProviderType,
        request_data: Dict[str, Any]
    ) -> IProvider:
        """Distribute request to optimal provider."""
        pass
    
    @abstractmethod
    async def update_provider_load(self, provider: IProvider, load_metric: float) -> None:
        """Update provider load metrics."""
        pass
    
    @abstractmethod
    async def get_provider_load_status(self) -> Dict[str, Dict[str, Any]]:
        """Get load status for all providers."""
        pass
    
    @abstractmethod
    async def rebalance_providers(self, provider_type: ProviderType) -> Dict[str, Any]:
        """Rebalance load across providers."""
        pass


class IProviderFailoverManager(ABC):
    """Interface for provider failover management."""
    
    @abstractmethod
    async def handle_provider_failure(
        self,
        failed_provider: IProvider,
        error: Exception,
        context: Dict[str, Any]
    ) -> Optional[IProvider]:
        """Handle provider failure and return fallback."""
        pass
    
    @abstractmethod
    async def mark_provider_unhealthy(
        self,
        provider_name: str,
        provider_type: ProviderType,
        reason: str
    ) -> None:
        """Mark provider as unhealthy."""
        pass
    
    @abstractmethod
    async def attempt_provider_recovery(
        self,
        provider_name: str,
        provider_type: ProviderType
    ) -> bool:
        """Attempt to recover unhealthy provider."""
        pass
    
    @abstractmethod
    async def get_failover_history(
        self,
        provider_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get failover history."""
        pass


class IProviderAnalytics(ABC):
    """Interface for provider analytics operations."""
    
    @abstractmethod
    async def analyze_provider_performance(
        self,
        provider_name: str,
        provider_type: ProviderType,
        time_range: str
    ) -> Dict[str, Any]:
        """Analyze provider performance over time."""
        pass
    
    @abstractmethod
    async def compare_providers(
        self,
        provider_type: ProviderType,
        metrics: List[str],
        time_range: str
    ) -> Dict[str, Any]:
        """Compare providers across metrics."""
        pass
    
    @abstractmethod
    async def get_optimization_recommendations(
        self,
        provider_type: ProviderType
    ) -> List[Dict[str, Any]]:
        """Get optimization recommendations."""
        pass
    
    @abstractmethod
    async def predict_provider_capacity(
        self,
        provider_name: str,
        provider_type: ProviderType,
        hours_ahead: int = 24
    ) -> Dict[str, Any]:
        """Predict provider capacity needs."""
        pass


class IProviderDiscovery(ABC):
    """Interface for provider discovery operations."""
    
    @abstractmethod
    async def discover_providers(self, provider_type: ProviderType) -> List[Dict[str, Any]]:
        """Discover available providers."""
        pass
    
    @abstractmethod
    async def auto_register_discovered_providers(self) -> Dict[str, Any]:
        """Auto-register discovered providers."""
        pass
    
    @abstractmethod
    async def validate_provider_availability(
        self,
        provider_name: str,
        provider_type: ProviderType
    ) -> bool:
        """Validate if provider is available."""
        pass


class IProviderCostManager(ABC):
    """Interface for provider cost management operations."""
    
    @abstractmethod
    async def calculate_provider_cost(
        self,
        provider_name: str,
        provider_type: ProviderType,
        usage_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate cost for provider usage."""
        pass
    
    @abstractmethod
    async def get_cost_breakdown(
        self,
        time_range: str,
        provider_type: Optional[ProviderType] = None
    ) -> Dict[str, Any]:
        """Get cost breakdown by provider."""
        pass
    
    @abstractmethod
    async def optimize_costs(self, provider_type: ProviderType) -> Dict[str, Any]:
        """Get cost optimization recommendations."""
        pass
    
    @abstractmethod
    async def set_cost_alerts(
        self,
        provider_name: str,
        provider_type: ProviderType,
        threshold: float
    ) -> str:
        """Set cost alert thresholds."""
        pass


class IProvidersFactory(ABC):
    """Factory interface for creating provider services - DIP compliance."""
    
    @abstractmethod
    def create_registry_service(self) -> IProviderRegistry:
        """Create provider registry service instance."""
        pass
    
    @abstractmethod
    def create_selector_service(self) -> IProviderSelector:
        """Create provider selector service instance."""
        pass
    
    @abstractmethod
    def create_health_service(self) -> IProviderHealthService:
        """Create provider health service instance."""
        pass
    
    @abstractmethod
    def create_cost_manager(self) -> IProviderCostManager:
        """Create provider cost manager instance."""
        pass