# src/providers/domain/provider.py
"""
Provider domain entities following domain-driven design principles.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from .interfaces import ProviderType, ProviderStatus, ProviderCapability, IProvider


@dataclass
class Provider: # Renomear BaseProvider para Provider
    """
    Represents a generic provider in the system.
    Implements IProvider interface.
    """
    name: str
    provider_type: ProviderType
    version: str = "1.0.0"
    capabilities: List[ProviderCapability] = field(default_factory=list)
    status: ProviderStatus = ProviderStatus.INACTIVE
    configuration: Dict[str, Any] = field(default_factory=dict)
    last_health_check: Optional[datetime] = None
    health_status: Optional[Dict[str, Any]] = None # Simplificar para um dict, ou usar uma classe de Health do monitoring

    def get_name(self) -> str:
        return self.name

    def get_type(self) -> ProviderType:
        return self.provider_type

    def get_version(self) -> str:
        return self.version

    def get_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities.copy()

    async def health_check(self) -> Dict[str, Any]:
        # Implementação básica de health check.
        # Idealmente, isso seria delegado a um serviço de monitoramento.
        return {
            "status": self.status.value,
            "last_check": datetime.utcnow().isoformat(),
            "message": "Basic health check performed"
        }

    def get_configuration(self) -> Dict[str, Any]:
        return self.configuration.copy()

    async def initialize(self, config: Dict[str, Any]) -> bool:
        self.configuration = config.copy()
        self.status = ProviderStatus.ACTIVE
        return True

    async def cleanup(self) -> None:
        self.status = ProviderStatus.INACTIVE
        self.configuration.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.provider_type.value,
            "version": self.version,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "configuration": self.configuration,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_status": self.health_status
        }
