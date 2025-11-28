# src/providers/api/routers.py
from typing import Annotated, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.providers.domain.interfaces import (
    IProviderRegistry,
    ProviderCapability,
    ProviderType,
)
from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User

from .dependencies import get_provider_registry
from .schemas import (
    ProviderCatalogEntry,
    ProviderDetailResponse,
    ProvidersListResponse,
    ProviderSummaryResponse,
)
from src.providers.domain.provider_metadata import get_provider_metadata

router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


def _list_provider_names(
    provider_registry: IProviderRegistry,
    provider_type: ProviderType,
) -> list[str]:
    """Return active provider names or fall back to the registered set."""

    providers = provider_registry.get_active_providers(provider_type)
    if not providers:
        providers = provider_registry.list_providers(provider_type)
    return sorted({provider.get_name() for provider in providers})


def _serialize_provider_map(provider_registry: IProviderRegistry) -> dict[str, list[str]]:
    """Build a dictionary keyed by provider type for quick dropdown usage."""

    relevant_types = (
        ProviderType.STORAGE,
        ProviderType.TRANSCRIPTION,
        ProviderType.SUMMARIZATION,
        ProviderType.SENTIMENT_ANALYSIS,
        ProviderType.TOPIC_MODELING,
    )
    return {
        provider_type.value: _list_provider_names(provider_registry, provider_type)
        for provider_type in relevant_types
    }


def _serialize_provider_catalog(provider_registry: IProviderRegistry) -> dict[str, list[ProviderCatalogEntry]]:
    relevant_types = (
        ProviderType.STORAGE,
        ProviderType.TRANSCRIPTION,
        ProviderType.SUMMARIZATION,
        ProviderType.SENTIMENT_ANALYSIS,
        ProviderType.TOPIC_MODELING,
    )

    catalog: dict[str, list[ProviderCatalogEntry]] = {}
    for provider_type in relevant_types:
        providers = provider_registry.list_providers(provider_type)
        entries: list[ProviderCatalogEntry] = []
        for provider in providers:
            metadata = get_provider_metadata(provider_type, provider.get_name())
            config = provider.get_configuration()
            entries.append(
                ProviderCatalogEntry(
                    name=provider.get_name(),
                    label=metadata.label if metadata else provider.get_name(),
                    description=metadata.description if metadata else "",
                    type=provider_type.value,
                    version=provider.get_version(),
                    status=provider.status.value,
                    capabilities=[cap.value for cap in provider.get_capabilities()],
                    is_default=bool(config.get("default")),
                )
            )
        catalog[provider_type.value] = entries
    return catalog


@router.get(
    "/",
    summary="Return provider names grouped by type",
    response_model=Dict[str, List[str]],
)
async def get_provider_name_map(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Expose a minimal provider catalogue for upload forms."""

    return _serialize_provider_map(provider_registry)


@router.get(
    "/catalog",
    summary="Return provider metadata grouped by type",
    response_model=Dict[str, List[ProviderCatalogEntry]],
)
async def get_provider_catalog(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> dict[str, list[ProviderCatalogEntry]]:
    """Expose enriched provider catalog for UI usage."""

    return _serialize_provider_catalog(provider_registry)


@router.get("/storage", summary="List storage providers", response_model=List[str])
async def list_storage_providers(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> list[str]:
    return _list_provider_names(provider_registry, ProviderType.STORAGE)


@router.get("/transcription", summary="List transcription providers", response_model=List[str])
async def list_transcription_providers(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> list[str]:
    return _list_provider_names(provider_registry, ProviderType.TRANSCRIPTION)


@router.get("/summarization", summary="List summarization providers", response_model=List[str])
async def list_summarization_providers(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> list[str]:
    return _list_provider_names(provider_registry, ProviderType.SUMMARIZATION)


@router.get("/sentiment", summary="List sentiment providers", response_model=List[str])
async def list_sentiment_providers(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> list[str]:
    return _list_provider_names(provider_registry, ProviderType.SENTIMENT_ANALYSIS)


@router.get("/topics", summary="List topic modeling providers", response_model=List[str])
async def list_topic_modeling_providers(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
) -> list[str]:
    return _list_provider_names(provider_registry, ProviderType.TOPIC_MODELING)


@router.get("/summary", response_model=ProviderSummaryResponse, summary="Get comprehensive provider summary")
async def get_provider_summary(
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive summary of all providers in the system."""
    try:
        # A lógica para obter o summary deve estar no IProviderRegistry ou em um serviço de aplicação
        # Por enquanto, vamos simular um summary básico
        all_providers = provider_registry.list_providers()
        summary_data = {
            "total_providers": len(all_providers),
            "active_providers": len(provider_registry.get_active_providers()),
            "providers_by_type": {
                pt.value: len(provider_registry.list_providers(pt)) for pt in ProviderType
            },
            "legacy_providers": {} # Remover ou adaptar se necessário
        }
        return ProviderSummaryResponse(**summary_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/list", response_model=ProvidersListResponse, summary="List providers with filtering")
async def list_providers(
    provider_type: Optional[ProviderType] = Query(None, description="Filter by provider type"),
    capability: Optional[ProviderCapability] = Query(None, description="Filter by capability"),
    active_only: bool = Query(True, description="Only return active providers"),
    *,
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
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
                "status": p.status.value # Acessar diretamente o status da entidade Provider
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
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
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

        # O método to_dict() da entidade Provider já retorna os dados formatados
        return ProviderDetailResponse(**provider.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Admin-only endpoints
@router.post("/admin/register", summary="Register new provider (admin only)")
async def register_provider(
    provider_data: dict, # Usar um Pydantic model para validação
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
    current_user: User = Depends(get_current_user),
):
    """Register a new provider (admin only)."""
    if not current_user.role or current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Esta lógica de criação e registro de provedor deve ser movida para um serviço de aplicação
        # ou um Command Handler. Por enquanto, é um placeholder.
        return {"message": "Provider registration endpoint - implementation needed"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/admin/{provider_type}/{provider_name}", summary="Unregister provider (admin only)")
async def unregister_provider(
    provider_type: ProviderType,
    provider_name: str,
    provider_registry: Annotated[IProviderRegistry, Depends(get_provider_registry)],
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
