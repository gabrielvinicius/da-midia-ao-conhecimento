# src/media_management/api/routers.py
import os
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
from ..config.settings import MediaSettings
from .dependencies import get_media_settings

router = APIRouter(
    prefix="/media",
    tags=["Media"],
)


@router.post("/", response_model=MediaResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new media file")
async def create_media(
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local", description="The storage provider to use (e.g., 'local', 's3')."),
    transcription_provider: Optional[str] = Query("whisper", description="The transcription provider to use."),
    summarization_provider: Optional[str] = Query("huggingface", description="The summarization provider to use."),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
    settings: MediaSettings = Depends(get_media_settings),
):
    """Uploads a new media file to start a processing pipeline."""
    try:
        # Validate file exists and has a name
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a filename")
        
        _, file_ext = os.path.splitext(file.filename)
        file_ext_lower = file_ext.lower()
        
        # Validate file extension
        if file_ext_lower not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid file format '{file_ext}'. Allowed formats: {', '.join(settings.allowed_extensions)}"
            )

        # Read file content to check actual size
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                detail=f"File too large ({file_size / (1024*1024):.2f}MB). Max size is {settings.max_file_size_mb}MB"
            )
        
        # Validate file is not empty
        if file_size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File cannot be empty")

        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=file_content,
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )
        media = await media_service.create_media(command)
        
        # Return a safe dictionary instead of using jsonable_encoder to avoid recursion
        return {
            "id": str(media.id),
            "original_file_path": media.original_file_path,
            "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
            "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
            "storage_provider": media.storage_provider,
            "transcription_provider": media.transcription_provider,
            "summarization_provider": media.summarization_provider,
            "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
            "user_id": str(media.user_id)
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Upload error for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Upload failed: {type(e).__name__}: {str(e)}"
        ) from e


@router.get("/", response_model=List[MediaResponse], summary="List all media for the current user")
async def get_all_media(
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media_list = await media_queries.list_by_user(user_id=str(current_user.id))
    
    # Convert to safe dictionary format to avoid recursion
    return [
        {
            "id": str(media.id),
            "original_file_path": media.original_file_path,
            "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
            "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
            "storage_provider": media.storage_provider,
            "transcription_provider": media.transcription_provider,
            "summarization_provider": media.summarization_provider,
            "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
            "user_id": str(media.user_id)
        }
        for media in media_list
    ]


@router.get("/{media_id}", response_model=MediaResponse, summary="Get a media item by its ID")
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
    
    # Return safe dictionary format to avoid recursion
    return {
        "id": str(media.id),
        "original_file_path": media.original_file_path,
        "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
        "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
        "storage_provider": media.storage_provider,
        "transcription_provider": media.transcription_provider,
        "summarization_provider": media.summarization_provider,
        "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
        "user_id": str(media.user_id)
    }
