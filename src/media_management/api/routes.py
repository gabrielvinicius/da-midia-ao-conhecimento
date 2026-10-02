# src/media_management/api/routers.py
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response

from src.media_management.application.errors import InvalidRangeError
from src.shared.domain.errors import NotFoundError
from src.media_management.application.dtos import (
    CreateMediaCommand,
    DeleteMediaCommand,
    GetMediaQuery,
    GetMediaStatisticsQuery,
    GetMediaStreamQuery,
    ListMediaQuery,
    ReprocessMediaCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.shared.infrastructure.middleware.correlation_middleware import correlation_id_of
from src.shared.application.schemas import (
    BaseResponseSchema,
    create_success_response,
)
from src.user_management.api.dependencies import get_current_user, get_current_user_from_query
from src.user_management.domain import User
from src.user_management.domain import UserRole

from .dependencies import get_media_service
from .schemas import MediaResponse

router = APIRouter(
    prefix="/media",
    tags=["Media"],
)


@router.post(
    "/",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new media file"
)
async def create_media(
    request: Request,
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    command = CreateMediaCommand(
        user_id=current_user.id,
        file=await file.read(),
        filename=file.filename,
        storage_provider=storage_provider,
        transcription_provider=transcription_provider,
        correlation_id=correlation_id_of(request),
    )
    # Erros de validação viram 400 nos tratadores globais; o resto, 500 sem
    # expor a mensagem interna.
    media = await service.create_media(command)
    return MediaResponse.from_domain(media)


@router.get(
    "/",
    response_model=dict,
    summary="List all media for the current user",
)
async def list_user_media(
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    order: str = Query("desc", pattern="^(asc|desc)$"),
):
    query = ListMediaQuery(
        user_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
        order=order,
    )
    page_data = await service.list_media(query)

    items = [
        MediaResponse.from_domain(media)
        for media in page_data.items
    ]

    return {
        "items": items,
        "total": page_data.total,
        "page": page_data.page,
        "pages": page_data.pages,
        "limit": page_data.limit,
    }


@router.get(
    "/stats",
    summary="Obter estatísticas das mídias do usuário atual",
)
async def media_stats(
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    query = GetMediaStatisticsQuery(user_id=current_user.id)
    stats = await service.get_media_statistics(query)
    return stats


@router.get(
    "/{media_id}",
    response_model=MediaResponse,
    summary="Get a media item by its ID",
)
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    media = await service.get_media(GetMediaQuery(media_id=media_id))
    # Mídia de outro usuário: 404, sem revelar que ela existe.
    if not media or (media.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise NotFoundError("Mídia não encontrada")
    return MediaResponse.from_domain(media)


@router.delete(
    "/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a media item",
)
async def delete_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    # Mídia de outro usuário: a política de acesso responde 404.
    await service.delete_media(
        DeleteMediaCommand(media_id=media_id), user_id=current_user.id, user_role=current_user.role
    )


@router.get("/{media_id}/stream", summary="Stream media bytes for playback")
async def stream_media(
    media_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user_from_query),
    service: MediaService = Depends(get_media_service),
):
    try:
        query = GetMediaStreamQuery(
            media_id=media_id,
            range_header=request.headers.get("range"),
        )
        stream_dto = await service.get_media_stream(
            query,
            user_id=current_user.id,
            user_role=current_user.role,
        )

        return Response(
            content=stream_dto.content,
            media_type=stream_dto.media_type,
            headers=stream_dto.headers,
            status_code=stream_dto.status_code,
        )
    except InvalidRangeError as exc:  # 416 é próprio do streaming
        raise HTTPException(status_code=416, detail=str(exc))


@router.post(
    "/{media_id}/reprocess",
    response_model=BaseResponseSchema,
    summary="Reprocess media item",
)
async def reprocess_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    """Reprocess a media item (transcription, summarization, sentiment)."""
    # Mídia de outro usuário: a política de acesso responde 404.
    await service.reprocess_media(
        ReprocessMediaCommand(media_id=media_id), user_id=current_user.id, user_role=current_user.role
    )
    return create_success_response(
        data={"media_id": str(media_id), "status": "processing", "message": "Media reprocessing initiated"},
        message="Media reprocessing started successfully",
    )
