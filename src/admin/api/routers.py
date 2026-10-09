"""Rotas do painel do administrador (o roteador inteiro exige administrador)."""
from dataclasses import asdict
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.admin.application.dtos import (
    GetMediaProcessingStatsQuery,
    GetSystemHealthQuery,
    GetSystemStatsQuery,
    GetUserActivityQuery,
)
from src.admin.application.services.admin_service import AdminService
from src.media_management.api.schemas import MediaResponse
from src.media_management.domain.enums import MediaStatus
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
from .schemas import (
    AdminMediaResponse,
    QueueItemResponse,
    QualityResponse,
    QueueResponse,
    CorrectedMedia,
    RatedComment,
    ServerStatusResponse,
    SystemStatsResponse,
    UserUpdateRequest,
)

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
    response_model=PaginatedResponse[AdminMediaResponse],
    summary="Mídias de todos os usuários",
)
async def list_all_media(
    service: AdminService = Depends(get_admin_service),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(
        None, description="Busca pelo nome do arquivo"
    ),
    status_filter: Optional[List[MediaStatus]] = Query(None, alias="status", description="Um ou mais estados."),
):
    result = await service.list_media(ListMediaQuery(page=page, limit=limit, search=search, status=status_filter))
    emails = await service.owner_emails(m.user_id for m in result.items)
    items = [
        AdminMediaResponse(**MediaResponse.from_domain(m).model_dump(), owner_email=emails.get(m.user_id))
        for m in result.items
    ]
    return PaginatedResponse[AdminMediaResponse](
        items=items,
        total=result.total,
        page=page,
        pages=result.pages if result.pages is not None else PaginatedResponse.pages_for(result.total, limit),
        limit=limit,
    )


@router.get("/queue", response_model=QueueResponse, summary="Fila de processamento")
async def get_processing_queue(service: AdminService = Depends(get_admin_service)):
    """Mídias em andamento na ordem de chegada, há quanto tempo cada uma está
    na etapa atual (e se parece parada) e as tarefas esperando no Celery."""
    snapshot = await service.get_queue()
    return QueueResponse(
        items=[QueueItemResponse(**asdict(item)) for item in snapshot.items],
        counts=snapshot.counts,
        broker=snapshot.broker,
        truncated=snapshot.truncated,
    )


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


@router.get("/server", response_model=ServerStatusResponse, summary="Máquina, GPU e serviços")
async def get_server_status(service: AdminService = Depends(get_admin_service)):
    """CPU, memória e GPU (placa inteira, lida pelo worker pesado), e se o banco,
    o Redis, o Ollama e os workers respondem."""
    server = await service.get_server_status()
    if server is None:
        raise HTTPException(status_code=503, detail="Leitura do servidor indisponível.")
    return ServerStatusResponse.model_validate(asdict(server))


@router.get("/quality", response_model=QualityResponse, summary="Qualidade da IA")
async def get_quality(service: AdminService = Depends(get_admin_service)):
    """Quanto da saída da IA os usuários corrigiram (resumo, temas, capítulos,
    perguntas e trechos da transcrição) e como a avaliaram."""
    report = await service.get_quality()
    if report is None:
        raise HTTPException(status_code=503, detail="Relatório de qualidade indisponível.")
    analyses, transcriptions, names = report["analyses"], report["transcriptions"], report["filenames"]
    return QualityResponse(
        analyses=analyses.analyses,
        corrected=analyses.corrected,
        useful=analyses.useful,
        not_useful=analyses.not_useful,
        useful_share=analyses.useful_share,
        recent_comments=[
            RatedComment(**asdict(f), filename=names.get(f.media_id)) for f in analyses.recent_comments
        ],
        recent_corrections=[
            CorrectedMedia(**asdict(c), filename=names.get(c.media_id)) for c in analyses.recent_corrections
        ],
        **asdict(transcriptions),
    )


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

