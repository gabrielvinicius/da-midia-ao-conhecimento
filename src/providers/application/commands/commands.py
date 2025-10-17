"""
Providers Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ConfigureProviderCommand:
    """Command to configure provider"""
    provider_type: str
    provider_name: str
    configuration: Dict[str, Any]
    is_active: bool = True


@dataclass(frozen=True)
class TestProviderCommand:
    """Command to test provider connection"""
    provider_name: str
    test_parameters: Optional[Dict[str, Any]] = None