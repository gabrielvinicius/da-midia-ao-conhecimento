# src/media_management/api/routers.py
import re
from typing import List, Optional
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
from src.shared.application.schemas import (
    BaseResponseSchema,
    create_error_response,
    create_success_response,
)
from src.shared.domain.errors import DomainError
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User
from src.user_management.domain import UserRole

from .dependencies import get_media_service
from .schemas import MediaResponse

router = APIRouter(
    prefix="/media",
    tags=["Media"],
)

logger = get_logger("media_api")

@router.post(
    "/",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new media file"
)
async def create_media(
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    summarization_provider: Optional[str] = Query(None),
    sentiment_provider: Optional[str] = Query(None),
    topic_modeling_provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    service: MediaService = Depends(get_media_service),
):
    try:
        file_content = await file.read()

        command = CreateMediaCommand(
            user_id=current_user.id,
            file=file_content,
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
        )

        media = await service.create_media(command)

        return MediaResponse.from_domain(media)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as exc:
        logger.error(
            "media_api.upload_failed",
            error=str(exc),
            exc_info=True,
            filename=file.filename if file else None,
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


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
    try:
        query = GetMediaQuery(media_id=media_id)
        media = await service.get_media(query)

        if not media:
            raise ValueError("Mídia não encontrada")

        if media.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise PermissionError("Não autorizado")

        return MediaResponse.from_domain(media)
    except (ValueError, PermissionError):
        raise HTTPException(
            status_code=404,
            detail="Media not found or not authorized",
        )


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
    try:
        command = DeleteMediaCommand(media_id=media_id)
        await service.delete_media(
            command,
            user_id=current_user.id,
            user_role=current_user.role,
        )
    except PermissionError:
        raise HTTPException(status_code=404, detail="Mídia não encontrada ou não autorizada")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{media_id}/stream", summary="Stream media bytes for playback")
async def stream_media(
    media_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("media_api.stream_failed", media_id=str(media_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Internal server error during streaming")


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
    try:
        command = ReprocessMediaCommand(media_id=media_id)
        await service.reprocess_media(
            command,
            user_id=current_user.id,
            user_role=current_user.role,
        )

        response_data = {
            "media_id": str(media_id),
            "status": "processing",
            "message": "Media reprocessing initiated"
        }

        return create_success_response(
            data=response_data,
            message="Media reprocessing started successfully"
        )

    except PermissionError:
        raise HTTPException(status_code=404, detail="Mídia não encontrada ou não autorizada")
    except ValueError as e:
        return create_error_response(
            error=str(e),
            message="Media reprocessing failed",
        )
    except Exception as e:
        return create_error_response(
            error=f"Media reprocessing failed: {str(e)}",
            message="Internal reprocessing error"
        )
