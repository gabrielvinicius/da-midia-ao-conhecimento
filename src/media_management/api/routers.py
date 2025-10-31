# src/media_management/api/routers.py
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query
from fastapi.encoders import jsonable_encoder

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User
from .dependencies import (
    get_media_lifecycle_service,
    get_media_query_service,
    get_media_upload_service,
)
from src.shared.api.unified_schemas import BaseResponseSchema, create_success_response, create_error_response

from ..application.services import (
    MediaLifecycleService,
    MediaQueryService,
    MediaUploadService,
)
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
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local"),
    transcription_provider: Optional[str] = Query(None),
    summarization_provider: Optional[str] = Query(None),
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
