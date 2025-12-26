from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.shared.application.provider_catalog import ProvidersResponse
from src.shared.application.services.providers_read_service import ProvidersReadService
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User

router = APIRouter(tags=["Providers"])


def get_providers_service(request: Request) -> ProvidersReadService:
    service = getattr(request.app.state, "providers_read_service", None)
    if service is None:
        raise RuntimeError(
            "ProvidersReadService não foi inicializado no app.state. "
            "Garanta que o lifespan configure `app.state.providers_read_service`."
        )
    return service


@router.get(
    "/providers",
    response_model=ProvidersResponse,
    summary="Lista providers selecionáveis no pipeline",
)
async def list_providers(
    _current_user: User = Depends(get_current_user),
    service: ProvidersReadService = Depends(get_providers_service),
) -> ProvidersResponse:
    return service.list_providers()


__all__ = ["router"]

