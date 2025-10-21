# src/providers/api/routers.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
# FIXED: Dependencies should come from application layer, not infrastructure
# This violates DDD - infrastructure should not be imported directly by API layer
from src.shared.application.unified_services import ServiceFactory
from src.shared.providers.simple_providers import provider_registry
from src.providers.domain.interfaces import ProviderType, ProviderCapability
from .dependencies import (
    get_provider_registry, get_provider_selector, get_provider_health_checker,
    get_provider_metrics
)
from .schemas import (
    ProviderSummaryResponse, ProviderDetailResponse, ProviderHealthResponse,
    ProvidersListResponse, ProviderSelectionRequest, ProviderSelectionResponse,
    ProviderMetricsResponse, SystemHealthResponse
)

router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


# Legacy endpoints for backward compatibility
@router.get("/legacy", summary="Legacy provider listing (deprecated)")
async def list_all_providers_legacy():
    """
    Returns all available providers organized by category.
    
    DEPRECATED: Use /providers/summary instead.
    """
    return {
        "storage": get_available_storage_providers(),
        "transcription": get_available_speech_recognition_providers(),
        "summarization": get_available_summarizer_providers()
    }


@router.get("/storage", response_model=List[str], summary="List available storage providers")
async def list_storage_providers() -> List[str]:
    """Returns a list of available storage providers (e.g., 'local', 's3')."""
    return get_available_storage_providers()


@router.get("/transcription", response_model=List[str], summary="List available transcription providers")
async def list_transcription_providers() -> List[str]:
    """Returns a list of available speech recognition providers (e.g., 'whisper', 'fastwhisper')."""
    return get_available_speech_recognition_providers()


@router.get("/summarization", response_model=List[str], summary="List available summarization providers")
async def list_summarization_providers() -> List[str]:
    """Returns a list of available summarization providers (e.g., 'huggingface')."""
    return get_available_summarizer_providers()


# New enhanced provider management endpoints
@router.get("/summary", response_model=ProviderSummaryResponse, summary="Get comprehensive provider summary")
async def get_provider_summary(
    provider_registry = Depends(get_provider_registry),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive summary of all providers in the system."""
    try:
        summary = provider_registry.get_provider_summary()
        
        # Add legacy provider information
        legacy_providers = {
            "storage": get_available_storage_providers(),
            "transcription": get_available_speech_recognition_providers(),
            "summarization": get_available_summarizer_providers()
        }
        
        return ProviderSummaryResponse(
            **summary,
            legacy_providers=legacy_providers
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/list", response_model=ProvidersListResponse, summary="List providers with filtering")
async def list_providers(
    provider_type: Optional[ProviderType] = Query(None, description="Filter by provider type"),
    capability: Optional[ProviderCapability] = Query(None, description="Filter by capability"),
    active_only: bool = Query(True, description="Only return active providers"),
    provider_registry = Depends(get_provider_registry),
    current_user: User = Depends(get_current_user),
):
    """List providers with advanced filtering options."""
    try:
        if capability:
            providers = provider_registry.get_providers_by_capability(capability)
        elif active_only:
            providers = provider_registry.get_active_providers(provider_type)
        else:
            providers = provider_registry.list_providers(provider_type)
        
        # Convert to response format
        provider_list = [
            {
                "name": p.get_name(),
                "type": p.get_type().value,
                "version": p.get_version(),
                "capabilities": [cap.value for cap in p.get_capabilities()],
                "status": getattr(p, 'status', 'unknown')
            }
            for p in providers
        ]
        
        return ProvidersListResponse(
            providers=provider_list,
            total_count=len(provider_list),
            filter_applied={
                "provider_type": provider_type.value if provider_type else None,
                "capability": capability.value if capability else None,
                "active_only": active_only
            }
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{provider_type}/{provider_name}", response_model=ProviderDetailResponse, summary="Get provider details")
async def get_provider_details(
    provider_type: ProviderType,
    provider_name: str,
    provider_registry = Depends(get_provider_registry),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific provider."""
    try:
        provider = provider_registry.get_provider(provider_name, provider_type)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider_name}' of type '{provider_type.value}' not found"
            )
        
        # Get health status if available
        health_status = None
        if hasattr(provider, 'health_status') and provider.health_status:
            health_status = provider.health_status.to_dict()
        
        return ProviderDetailResponse(
            name=provider.get_name(),
            type=provider.get_type().value,
            version=provider.get_version(),
            capabilities=[cap.value for cap in provider.get_capabilities()],
            configuration=provider.get_configuration(),
            health_status=health_status,
            metadata=getattr(provider, 'metadata', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health/check", response_model=ProviderHealthResponse, summary="Check provider health")
async def check_providers_health(
    provider_type: Optional[ProviderType] = Query(None, description="Filter by provider type"),
    provider_health_checker = Depends(get_provider_health_checker),
    current_user: User = Depends(get_current_user),
):
    """Perform health check on providers."""
    try:
        health_results = await provider_health_checker.check_all_providers_health(provider_type)
        
        return ProviderHealthResponse(
            health_results=health_results,
            timestamp="2024-01-01T00:00:00Z",  # Would use actual timestamp
            overall_status="healthy" if health_results else "no_providers"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/health/system", response_model=SystemHealthResponse, summary="Get system health summary")
async def get_system_health_summary(
    provider_health_checker = Depends(get_provider_health_checker),
    current_user: User = Depends(get_current_user),
):
    """Get overall system health summary."""
    try:
        health_summary = await provider_health_checker.get_system_health_summary()
        
        return SystemHealthResponse(**health_summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/select", response_model=ProviderSelectionResponse, summary="Select optimal provider")
async def select_provider(
    request: ProviderSelectionRequest,
    provider_selector = Depends(get_provider_selector),
    current_user: User = Depends(get_current_user),
):
    """Select optimal provider based on criteria."""
    try:
        # Convert string capabilities to enums
        capabilities = []
        if request.required_capabilities:
            for cap_str in request.required_capabilities:
                try:
                    capabilities.append(ProviderCapability(cap_str))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid capability: {cap_str}"
                    )
        
        selected_provider = await provider_selector.select_best_provider(
            provider_type=request.provider_type,
            required_capabilities=capabilities,
            preferences=request.preferences
        )
        
        if not selected_provider:
            return ProviderSelectionResponse(
                selected_provider=None,
                selection_reason="No providers match the specified criteria",
                alternatives=[]
            )
        
        # Get alternative providers for load balancing
        alternatives = await provider_selector.select_providers_for_load_balancing(
            provider_type=request.provider_type,
            required_capabilities=capabilities,
            count=3
        )
        
        # Remove selected provider from alternatives
        alternatives = [p for p in alternatives if p.get_name() != selected_provider.get_name()]
        
        return ProviderSelectionResponse(
            selected_provider={
                "name": selected_provider.get_name(),
                "type": selected_provider.get_type().value,
                "version": selected_provider.get_version(),
                "capabilities": [cap.value for cap in selected_provider.get_capabilities()]
            },
            selection_reason=f"Selected using {request.preferences.get('load_balancing_strategy', 'round_robin')} strategy",
            alternatives=[
                {
                    "name": p.get_name(),
                    "type": p.get_type().value,
                    "version": p.get_version(),
                    "capabilities": [cap.value for cap in p.get_capabilities()]
                }
                for p in alternatives[:2]  # Limit to 2 alternatives
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/metrics/{provider_type}/{provider_name}", response_model=ProviderMetricsResponse, summary="Get provider metrics")
async def get_provider_metrics(
    provider_type: ProviderType,
    provider_name: str,
    provider_metrics = Depends(get_provider_metrics),
    current_user: User = Depends(get_current_user),
):
    """Get metrics for a specific provider."""
    try:
        performance_metrics = await provider_metrics.get_provider_performance_metrics(
            provider_name, provider_type
        )
        
        reliability_metrics = await provider_metrics.get_provider_reliability_metrics(
            provider_name, provider_type
        )
        
        cost_metrics = await provider_metrics.get_cost_metrics(
            provider_name, provider_type
        )
        
        return ProviderMetricsResponse(
            provider_name=provider_name,
            provider_type=provider_type.value,
            performance_metrics=performance_metrics,
            reliability_metrics=reliability_metrics,
            cost_metrics=cost_metrics,
            last_updated="2024-01-01T00:00:00Z"  # Would use actual timestamp
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin-only endpoints
@router.post("/admin/register", summary="Register new provider (admin only)")
async def register_provider(
    provider_data: dict,
    provider_registry = Depends(get_provider_registry),
    current_user: User = Depends(get_current_user),
):
    """Register a new provider (admin only)."""
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # This would create and register a new provider
        # Implementation depends on the specific provider type
        return {"message": "Provider registration endpoint - implementation needed"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/admin/{provider_type}/{provider_name}", summary="Unregister provider (admin only)")
async def unregister_provider(
    provider_type: ProviderType,
    provider_name: str,
    provider_registry = Depends(get_provider_registry),
    current_user: User = Depends(get_current_user),
):
    """Unregister a provider (admin only)."""
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        success = provider_registry.unregister_provider(provider_name, provider_type)
        
        if success:
            return {"message": f"Provider '{provider_name}' unregistered successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{provider_name}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
