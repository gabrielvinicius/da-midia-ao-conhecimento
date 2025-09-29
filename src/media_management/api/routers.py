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
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=MediaResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new media file")
async def create_media(
    file: UploadFile = File(...),
    storage_provider: Optional[str] = Query("local", description="The storage provider to use (e.g., 'local', 's3')."),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
):
    """Uploads a new media file (video, audio, or text) to start a processing pipeline."""
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
