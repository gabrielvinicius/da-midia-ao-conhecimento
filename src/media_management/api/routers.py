# src/media_management/api/routers.py
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query
from fastapi.encoders import jsonable_encoder

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_media_service, get_media_queries
from ..application.commands.create_media_command import CreateMediaCommand
from ..application.media_service import MediaService
from ..application.queries.media_queries import MediaQueries
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
    storage_provider: Optional[str] = Query("local", description="The storage provider to use (e.g., 'local', 's3')."),
    transcription_provider: Optional[str] = Query(None, description="The transcription provider to use."),
    summarization_provider: Optional[str] = Query(None, description="The summarization provider to use."),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
):
    """Uploads a new media file and specifies which AI providers to use."""
    try:
        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=await file.read(),
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )
        media = await media_service.create_media(command)
        return jsonable_encoder(media)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)}") from e


@router.get("/", response_model=List[MediaResponse], summary="List all media for the current user")
async def list_user_media(
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media_list = await media_queries.list_by_user(user_id=str(current_user.id))
    return jsonable_encoder(media_list)


@router.get("/{media_id}", response_model=MediaResponse, summary="Get a media item by its ID")
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
    return jsonable_encoder(media)
