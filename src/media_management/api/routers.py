# src/media_management/api/routers.py
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query
from fastapi.encoders import jsonable_encoder

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import (
    get_create_media_handler, 
    get_media_queries, 
    get_media_authorization_service
)
from src.shared.api.unified_schemas import BaseResponseSchema, create_success_response, create_error_response

from ..application.commands.create_media_command import CreateMediaCommand
from ..application.commands.create_media_command_handler import CreateMediaCommandHandler
from ..application.queries.media_queries import MediaQueries
from ..application.services.media_authorization_service import MediaAuthorizationService
from .schemas import MediaResponse
from ..config.settings import MediaSettings

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
    create_media_handler: CreateMediaCommandHandler = Depends(get_create_media_handler),
):
    try:
        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=await file.read(),
            filename=file.filename,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            summarization_provider=summarization_provider
        )
        media = await create_media_handler.handle(command)
        return jsonable_encoder(media)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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
    auth_service: MediaAuthorizationService = Depends(get_media_authorization_service),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or not auth_service.authorize_media_access(media, current_user):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
    return jsonable_encoder(media)


@router.post("/{media_id}/reprocess", response_model=BaseResponseSchema, summary="Reprocess media item")
async def reprocess_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    auth_service: MediaAuthorizationService = Depends(get_media_authorization_service),
):
    """Reprocess a media item (transcription, summarization, sentiment analysis, etc.)"""
    try:
        # Validate media access
        media = await media_queries.get_by_id(str(media_id))
        if not media or not auth_service.authorize_media_access(media, current_user):
            raise HTTPException(status_code=404, detail="Media not found or not authorized")

        # TODO: Implement actual reprocessing logic
        # This should trigger the media processing pipeline again
        response_data = {
            "media_id": str(media_id),
            "status": "processing",
            "message": "Media reprocessing initiated"
        }
        
        return create_success_response(
            data=response_data,
            message="Media reprocessing started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return create_error_response(
            error=f"Media reprocessing failed: {str(e)}",
            message="Internal reprocessing error"
        )
