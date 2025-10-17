"""
Provider domain entities following domain-driven design principles.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .interfaces import ProviderType, ProviderStatus, ProviderCapability, IProvider


@dataclass
class ProviderMetadata:
    """Metadata for a provider."""
    name: str
    version: str
    description: str
    vendor: str
    documentation_url: Optional[str] = None
    support_url: Optional[str] = None
    pricing_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProviderConfiguration:
    """Configuration for a provider."""
    provider_name: str
    provider_type: ProviderType
    config_data: Dict[str, Any]
    is_sensitive: bool = False
    environment: str = "production"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def mask_sensitive_data(self) -> Dict[str, Any]:
        """Return configuration with sensitive data masked."""
        if not self.is_sensitive:
            return self.config_data
        
        masked_config = {}
        for key, value in self.config_data.items():
            if any(sensitive in key.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                masked_config[key] = "*" * len(str(value)) if value else None
            else:
                masked_config[key] = value
        
        return masked_config


@dataclass
class ProviderHealth:
    """Health status of a provider."""
    provider_name: str
    provider_type: ProviderType
    status: ProviderStatus
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    consecutive_failures: int = 0
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy."""
        return self.status == ProviderStatus.ACTIVE and self.error_message is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider_name": self.provider_name,
            "provider_type": self.provider_type.value,
            "status": self.status.value,
            "last_check": self.last_check.isoformat(),
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "details": self.details,
            "consecutive_failures": self.consecutive_failures,
            "is_healthy": self.is_healthy()
        }


@dataclass
class ProviderMetrics:
    """Metrics for a provider."""
    provider_name: str
    provider_type: ProviderType
    
    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0
    
    # Reliability metrics
    uptime_percentage: float = 100.0
    error_rate_percentage: float = 0.0
    last_failure: Optional[datetime] = None
    
    # Cost metrics
    total_cost: float = 0.0
    cost_per_request: float = 0.0
    
    # Load metrics
    current_load: float = 0.0
    max_capacity: float = 100.0
    
    # Timestamps
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    def get_load_percentage(self) -> float:
        """Calculate current load as percentage of capacity."""
        if self.max_capacity == 0:
            return 0.0
        return (self.current_load / self.max_capacity) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "provider_name": self.provider_name,
            "provider_type": self.provider_type.value,
            "performance": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate_percentage": self.get_success_rate(),
                "average_response_time_ms": self.average_response_time_ms,
                "total_processing_time_ms": self.total_processing_time_ms
            },
            "reliability": {
                "uptime_percentage": self.uptime_percentage,
                "error_rate_percentage": self.error_rate_percentage,
                "last_failure": self.last_failure.isoformat() if self.last_failure else None
            },
            "cost": {
                "total_cost": self.total_cost,
                "cost_per_request": self.cost_per_request
            },
            "load": {
                "current_load": self.current_load,
                "max_capacity": self.max_capacity,
                "load_percentage": self.get_load_percentage()
            },
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            }
        }


@dataclass
class ProviderFailover:
    """Failover event for a provider."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    primary_provider: str = ""
    fallback_provider: str = ""
    provider_type: ProviderType = ProviderType.STORAGE
    failure_reason: str = ""
    recovery_action: str = ""
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_resolved(self) -> bool:
        """Check if failover has been resolved."""
        return self.resolved_at is not None
    
    def resolve(self, recovery_action: str) -> None:
        """Mark failover as resolved."""
        self.resolved_at = datetime.utcnow()
        self.recovery_action = recovery_action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "primary_provider": self.primary_provider,
            "fallback_provider": self.fallback_provider,
            "provider_type": self.provider_type.value,
            "failure_reason": self.failure_reason,
            "recovery_action": self.recovery_action,
            "occurred_at": self.occurred_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_resolved": self.is_resolved(),
            "context": self.context
        }


class BaseProvider(IProvider):
    """
    Base implementation for providers.
    
    Provides common functionality that all providers can inherit.
    """
    
    def __init__(
        self,
        name: str,
        provider_type: ProviderType,
        version: str = "1.0.0",
        capabilities: Optional[List[ProviderCapability]] = None,
        metadata: Optional[ProviderMetadata] = None
    ):
        self.name = name
        self.provider_type = provider_type
        self.version = version
        self.capabilities = capabilities or []
        self.metadata = metadata or ProviderMetadata(
            name=name,
            version=version,
            description=f"{name} provider",
            vendor="Internal"
        )
        self.status = ProviderStatus.INACTIVE
        self.configuration: Dict[str, Any] = {}
        self.last_health_check: Optional[datetime] = None
        self.health_status: Optional[ProviderHealth] = None
    
    def get_name(self) -> str:
        """Get provider name."""
        return self.name
    
    def get_type(self) -> ProviderType:
        """Get provider type."""
        return self.provider_type
    
    def get_version(self) -> str:
        """Get provider version."""
        return self.version
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Get provider capabilities."""
        return self.capabilities.copy()
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get provider configuration."""
        return self.configuration.copy()
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize provider with configuration."""
        try:
            self.configuration = config.copy()
            # Subclasses should override this for specific initialization
            self.status = ProviderStatus.ACTIVE
            return True
        except Exception:
            self.status = ProviderStatus.ERROR
            return False
    
    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        self.status = ProviderStatus.INACTIVE
        self.configuration.clear()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform basic health check."""
        start_time = datetime.utcnow()
        
        try:
            # Basic health check - subclasses should override
            is_healthy = self.status == ProviderStatus.ACTIVE
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.health_status = ProviderHealth(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=self.status,
                last_check=datetime.utcnow(),
                response_time_ms=response_time,
                error_message=None if is_healthy else "Provider not active"
            )
            
            self.last_health_check = datetime.utcnow()
            
            return self.health_status.to_dict()
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.health_status = ProviderHealth(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderStatus.ERROR,
                last_check=datetime.utcnow(),
                response_time_ms=response_time,
                error_message=str(e)
            )
            
            return self.health_status.to_dict()
    
    def has_capability(self, capability: ProviderCapability) -> bool:
        """Check if provider has specific capability."""
        return capability in self.capabilities
    
    def add_capability(self, capability: ProviderCapability) -> None:
        """Add capability to provider."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    def remove_capability(self, capability: ProviderCapability) -> None:
        """Remove capability from provider."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
    
    def update_metadata(self, metadata: ProviderMetadata) -> None:
        """Update provider metadata."""
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert provider to dictionary."""
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "version": self.version,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "configuration": self.configuration,
            "metadata": {
                "description": self.metadata.description,
                "vendor": self.metadata.vendor,
                "documentation_url": self.metadata.documentation_url,
                "support_url": self.metadata.support_url,
                "tags": self.metadata.tags
            },
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_status": self.health_status.to_dict() if self.health_status else None
        }


@dataclass
class ProviderSelectionCriteria:
    """Criteria for selecting providers."""
    provider_type: ProviderType
    required_capabilities: List[ProviderCapability] = field(default_factory=list)
    preferred_providers: List[str] = field(default_factory=list)
    excluded_providers: List[str] = field(default_factory=list)
    max_response_time_ms: Optional[float] = None
    min_success_rate: Optional[float] = None
    max_cost_per_request: Optional[float] = None
    load_balancing_strategy: str = "round_robin"  # round_robin, least_loaded, random
    failover_enabled: bool = True
    
    def matches_provider(self, provider: IProvider, metrics: Optional[ProviderMetrics] = None) -> bool:
        """Check if provider matches selection criteria."""
        # Check type
        if provider.get_type() != self.provider_type:
            return False
        
        # Check excluded providers
        if provider.get_name() in self.excluded_providers:
            return False
        
        # Check required capabilities
        provider_capabilities = provider.get_capabilities()
        for required_cap in self.required_capabilities:
            if required_cap not in provider_capabilities:
                return False
        
        # Check metrics if provided
        if metrics:
            if self.max_response_time_ms and metrics.average_response_time_ms > self.max_response_time_ms:
                return False
            
            if self.min_success_rate and metrics.get_success_rate() < self.min_success_rate:
                return False
            
            if self.max_cost_per_request and metrics.cost_per_request > self.max_cost_per_request:
                return False
        
        return True