"""Rotas do painel do administrador (o roteador inteiro exige administrador)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.admin.application.dtos import (
    GetMediaProcessingStatsQuery,
    GetSystemHealthQuery,
    GetSystemStatsQuery,
    GetUserActivityQuery,
)
from src.admin.application.services.admin_service import AdminService
from src.media_management.api.schemas import MediaResponse, media_page
from src.media_management.application.dtos import (
    ListMediaQuery,
)
from src.shared.api.schemas import PaginatedResponse
from src.user_management.api.dependencies import get_current_admin_user
from src.user_management.api.schemas import UserResponse
from src.user_management.application.dtos import ListUsersQuery
from src.user_management.domain import User

from .dependencies import (
    get_admin_service,
)
from .schemas import SystemStatsResponse, UserUpdateRequest

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)],
)


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Estatísticas gerais",
)
async def get_system_stats(service: AdminService = Depends(get_admin_service)):
    return await service.get_system_stats(GetSystemStatsQuery())


@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    summary="Usuários",
)
async def list_all_users(
    service: AdminService = Depends(get_admin_service),
    page: int = Query(1, ge=1, description="Página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    search: Optional[str] = Query(None, description="Busca pelo e-mail"),
):
    result = await service.list_users(
        ListUsersQuery(page=page, limit=limit, search=search)
    )
    return PaginatedResponse[UserResponse](
        items=result["items"],
        total=result["total_items"],
        page=result["current_page"],
        pages=result["total_pages"],
        limit=limit,
    )


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Alterar o perfil de um usuário",
)
async def update_user(
    user_id: UUID,
    update_data: UserUpdateRequest,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    return await service.update_user_role(
        user_id=user_id,
        new_role=update_data.role,
        admin_user=current_admin,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir um usuário",
)
async def delete_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    await service.delete_user(
        user_id=user_id,
        admin_user=current_admin,
    )



@router.get(
    "/media",
    response_model=PaginatedResponse[MediaResponse],
    summary="Mídias de todos os usuários",
)
async def list_all_media(
    service: AdminService = Depends(get_admin_service),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(
        None, description="Busca pelo nome do arquivo"
    ),
):
    result = await service.list_media(ListMediaQuery(page=page, limit=limit, search=search))
    return media_page(result, page, limit)


@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir uma mídia",
)
async def delete_media(
    media_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    await service.delete_media(
        media_id=media_id,
        admin_user=current_admin,
    )


@router.post(
    "/media/{media_id}/reprocess",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reprocessar uma mídia que falhou",
)
async def reprocess_media(
    media_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    await service.reprocess_media(
        media_id=media_id,
        admin_user=current_admin,
    )
    return {"message": "Reprocessamento iniciado."}


@router.get("/stats/health", summary="Alertas do sistema")
async def get_system_health(service: AdminService = Depends(get_admin_service)):
    return await service.get_system_health(GetSystemHealthQuery())


@router.get(
    "/stats/processing-times",
    summary="Durações de transcrição e de cada etapa da análise",
)
async def get_processing_times(
    days: Optional[int] = Query(None, ge=1, le=365, description="Últimos N dias; vazio = tudo."),
    service: AdminService = Depends(get_admin_service),
):
    """Execuções, falhas, média, mediana, máximo e fator de tempo real por tarefa."""
    return await service.get_processing_times(days)


@router.get(
    "/stats/media-processing",
    summary="Mídias por estado",
)
async def get_media_processing_stats(
    service: AdminService = Depends(get_admin_service),
):
    return await service.get_media_processing_stats(GetMediaProcessingStatsQuery())


@router.get("/users/{user_id}/activity", summary="Atividade de um usuário")
async def get_user_activity(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    return await service.get_user_activity(
        query=GetUserActivityQuery(user_id=user_id)
    )


@router.post(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    summary="Reativar uma conta",
)
async def activate_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    return await service.activate_user(user_id=user_id, admin_user=current_admin)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Desativar uma conta",
)
async def deactivate_user(
    user_id: UUID,
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
):
    return await service.deactivate_user(user_id=user_id, admin_user=current_admin)


@router.post("/media/bulk-reprocess", summary="Reprocessar um lote de mídias que falharam")
async def bulk_reprocess_failed_media(
    service: AdminService = Depends(get_admin_service),
    current_admin: User = Depends(get_current_admin_user),
    limit: int = Query(50, ge=1, le=200, description="Máximo de mídias neste pedido"),
):
    """Reprocessa até ``limit`` mídias com falha, das mais antigas para as mais
    novas; ``more_pending`` indica que há outras para um próximo pedido."""
    result = await service.bulk_reprocess_failed_media(admin_user=current_admin, limit=limit)
    return {
        "reprocessed_count": result.reprocessed,
        "failed_count": result.failed,
        "more_pending": result.more_pending,
    }

