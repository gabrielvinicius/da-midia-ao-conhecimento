# src/media_management/api/routers.py
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import (
    BaseResponseSchema,
    create_error_response,
    create_success_response,
)
from src.user_management.domain.user import User

from ..application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)
from .dependencies import (
    get_media_lifecycle_service,
    get_media_query_service,
    get_media_upload_service,
)
from .schemas import MediaResponse
from src.storage.infrastructure.dependencies import StorageServiceFactory


RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d+)-(\d+)?")

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
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    summarization_provider: Optional[str] = Query(None),
    sentiment_provider: Optional[str] = Query(None),
    topic_modeling_provider: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    media_upload_service: MediaUploadService = Depends(get_media_upload_service),
):
    try:
        file_content = await file.read()
        media = await media_upload_service.create_media(
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider,
            sentiment_provider=sentiment_provider,
            topic_modeling_provider=topic_modeling_provider,
        )
        return jsonable_encoder(media)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[MediaResponse], summary="List all media for the current user")
async def list_user_media(
    current_user: User = Depends(get_current_user),
    media_query_service: MediaQueryService = Depends(get_media_query_service),
):
    media_list = await media_query_service.list_media_for_user(user_id=current_user.id)
    return jsonable_encoder(media_list)

@router.get("/{media_id}", response_model=MediaResponse, summary="Get a media item by its ID")
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_query_service: MediaQueryService = Depends(get_media_query_service),
):
    try:
        media = await media_query_service.get_media_for_user(
            media_id=media_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )
    except (ValueError, PermissionError):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")

    return jsonable_encoder(media)


@router.get("/{media_id}/stream", summary="Stream media bytes for playback")
async def stream_media(
    media_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    media_query_service: MediaQueryService = Depends(get_media_query_service),
):
    try:
        media = await media_query_service.get_media_for_user(
            media_id=media_id,
            user_id=current_user.id,
            user_role=current_user.role,
        )
    except (ValueError, PermissionError):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")

    if not media.original_file_path:
        raise HTTPException(status_code=404, detail="Media file unavailable")

    storage_provider = getattr(media, "storage_provider", None) or "local"
    storage_factory = StorageServiceFactory()
    storage_client = storage_factory.get_download_service(storage_provider)

    try:
        file_bytes = await storage_client.download_file(media.original_file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Media file missing from storage")

    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(status_code=404, detail="Media file is empty")

    filename = media.filename or media.original_file_path.split("/")[-1]
    mime_type = getattr(media, "mime_type", None) or "application/octet-stream"

    range_header = request.headers.get("range")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{filename}"',
    }

    if range_header:
        range_header = range_header.strip()
        match = RANGE_HEADER_PATTERN.match(range_header)
        if not match:
            raise HTTPException(status_code=416, detail="Invalid Range header")

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) is not None else file_size - 1
        if start >= file_size:
            raise HTTPException(status_code=416, detail="Requested range not satisfiable")

        end = min(end, file_size - 1)
        payload = file_bytes[start : end + 1]
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(len(payload))
        status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        payload = file_bytes
        headers["Content-Length"] = str(file_size)
        status_code = status.HTTP_200_OK

    return Response(content=payload, media_type=mime_type, headers=headers, status_code=status_code)


@router.post("/{media_id}/reprocess", response_model=BaseResponseSchema, summary="Reprocess media item")
async def reprocess_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_lifecycle_service: MediaLifecycleService = Depends(get_media_lifecycle_service),
):
    """Reprocess a media item (transcription, summarization, sentiment analysis, etc.)"""
    try:
        await media_lifecycle_service.reprocess_media(
            media_id=media_id,
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
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
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
