# src/media_management/api/routers.py
from typing import Optional
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query
from fastapi.encoders import jsonable_encoder

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_media_service
from ..application.commands.create_media_command import CreateMediaCommand
from ..application.media_service import MediaService
from .schemas import MediaResponse

router = APIRouter(
    prefix="/media",
    tags=["Media"],
)


@router.post(
    "/", 
    response_model=MediaResponse, 
    status_code=status.HTTP_201_CREATED, 
    summary="Upload a new media file",
    description="""
Uploads a new media file (video, audio, or text). This is the main entry point for the processing pipeline.

This endpoint is asynchronous. It returns immediately with the initial media record and triggers a background process based on the media type:
- **VIDEO**: Triggers audio extraction.
- **AUDIO**: Triggers transcription.
- **TEXT**: Triggers text extraction (e.g., from a PDF).
""",
    responses={
        400: {"description": "Invalid file type or bad request"},
        401: {"description": "Unauthorized"},
        413: {"description": "File too large"},
        500: {"description": "Internal server error during upload"},
    }
)
async def create_media(
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local", description="The storage provider to use (e.g., 'local', 's3')."),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
):
    try:
        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=await file.read(),
            filename=file.filename,
            storage_provider=storage_provider
        )
        media = await media_service.create_media(command)
        return jsonable_encoder(media)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Upload failed: {str(e)}") from e
