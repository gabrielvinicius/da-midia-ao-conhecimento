from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.providers.domain.interfaces import (
    ProviderCapability,
    ProviderStatus,
    ProviderType,
)


@dataclass
class Provider:
    name: str
    provider_type: ProviderType
    status: ProviderStatus
    capabilities: List[ProviderCapability]
    configuration: Dict[str, Any] = field(default_factory=dict)
    display_name: Optional[str] = None
    description: Optional[str] = None

    # Compatibility helpers
    def get_name(self) -> str:
        return self.name

    def get_type(self) -> ProviderType:
        return self.provider_type

    def get_version(self) -> str:
        return self.configuration.get("version", "unknown")

    def get_capabilities(self) -> List[ProviderCapability]:
        return self.capabilities
