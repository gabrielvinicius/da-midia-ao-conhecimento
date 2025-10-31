# src/providers/api/schemas.py
"""
Providers API Schemas - Pydantic models for provider endpoints
Follows clear data contracts and validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.providers.domain.interfaces import ProviderType, ProviderCapability


# Request Schemas
class ProviderRegistrationRequest(BaseModel):
    """Request schema for provider registration."""
    name: str = Field(..., description="Provider name")
    provider_type: ProviderType = Field(..., description="Provider type")
    version: str = Field("1.0.0", description="Provider version")
    capabilities: List[str] = Field(default_factory=list, description="Provider capabilities")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Provider configuration")
    # metadata: Optional[Dict[str, Any]] = Field(None, description="Provider metadata") # Removido, pois ProviderMetadata foi removido


# Response Schemas
class ProviderInfo(BaseModel):
    """Basic provider information."""
    name: str
    type: str
    version: str
    capabilities: List[str]
    status: Optional[str] = None


class ProviderSummaryResponse(BaseModel):
    """Response schema for provider summary."""
    total_providers: int
    providers_by_type: Dict[str, int]
    active_providers: int
    # capabilities_coverage: Dict[str, int] # Removido, pois não há lógica para isso
    # initialized: bool # Removido, pois não há lógica para isso
    legacy_providers: Optional[Dict[str, List[str]]] = None


class ProvidersListResponse(BaseModel):
    """Response schema for provider listing."""
    providers: List[ProviderInfo]
    total_count: int
    filter_applied: Dict[str, Any]


class ProviderDetailResponse(BaseModel):
    """Response schema for detailed provider information."""
    name: str
    type: str
    version: str
    capabilities: List[str]
    configuration: Dict[str, Any]
    health_status: Optional[Dict[str, Any]] = None
    # metadata: Optional[Dict[str, Any]] = None # Removido, pois ProviderMetadata foi removido
