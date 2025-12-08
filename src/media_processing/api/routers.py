from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status, Query

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.user_management.api.dependencies import get_current_user
from src.shared.application.schemas import (
    BaseResponseSchema,
    create_error_response,
    create_success_response,
)
from src.user_management.domain.user import User
from src.media_management.api.dependencies import get_media_service

from src.media_management.application.services.media_service import MediaService

from src.media_processing.application.commands.dto import (
    ReprocessTranscriptionCommand,
    SetSpeakerAliasesCommand,
)
from src.media_management.application.services.media_service import MediaService
from src.media_processing.application.queries.dto import (
    GetTranscriptionByIdQuery,
    GetTranscriptionByMediaIdQuery,
)

from .dependencies import (
    get_transcription_service,
)
from .schemas import SpeakerAliasesUpdateRequest, TranscriptionResponse

from src.media_management.application.services.media_service import MediaService
from src.media_management.application.queries.dto import GetMediaQuery

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.put("/{transcription_id}/speaker-aliases", response_model=BaseResponseSchema, summary="Set Speaker Aliases for a Transcription")
async def set_speaker_aliases(
    transcription_id: UUID, # Path parameter
    request_data: SpeakerAliasesUpdateRequest, # Request body
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    current_user: User = Depends(get_current_user),
):
    """Endpoint to set or update the speaker aliases for a given transcription."""
    try:
        command = SetSpeakerAliasesCommand(
            transcription_id=transcription_id,
            aliases=request_data.aliases,
        )
        result = await transcription_service.set_speaker_aliases(command)
        return create_success_response(data=result, message="Speaker aliases set successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=TranscriptionResponse, summary="Get a transcription by its Media ID")
async def get_transcription_by_media_id(
    media_id: UUID = Query(..., description="Media ID to get transcription for."),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    current_user: User = Depends(get_current_user),
):
    query = GetTranscriptionByMediaIdQuery(media_id=media_id)
    transcription = await transcription_service.get_transcription_by_media_id(query)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found for the given media ID")
    
    # Explicit mapping
    return TranscriptionResponse(
        id=transcription.id,
        media_id=transcription.media_id,
        content=transcription.content,
        language=transcription.language,
        status=transcription.status.value,
        confidence_score=transcription.confidence_score,
        created_at=transcription.created_at,
        processed_at=transcription.processed_at,
        speaker_labels=transcription.speaker_labels,
        segments=transcription.segments,
        error_message=transcription.error_message
    )


@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Get a transcription by its ID")
async def get_transcription_by_id(
    transcription_id: UUID,
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    current_user: User = Depends(get_current_user),
):
    query = GetTranscriptionByIdQuery(transcription_id=transcription_id)
    transcription = await transcription_service.get_transcription_by_id(query)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
    
    # Explicit mapping
    return TranscriptionResponse(
        id=transcription.id,
        media_id=transcription.media_id,
        content=transcription.content,
        language=transcription.language,
        status=transcription.status.value,
        confidence_score=transcription.confidence_score,
        created_at=transcription.created_at,
        processed_at=transcription.processed_at,
        speaker_labels=transcription.speaker_labels,
        segments=transcription.segments,
        error_message=transcription.error_message
    )


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess transcription")
async def reprocess_transcription(
    command: ReprocessTranscriptionCommand, # Use the DTO
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    media_service: MediaService = Depends(get_media_service), # Changed from media_queries
    current_user: User = Depends(get_current_user),
):
    """Reprocess transcription for existing media
    Useful for: changing providers, languages, or fixing failed transcriptions
    """
    try:
        # Check ownership logic should be in a policy or adapter in media_management
        # For now, keep it here.
        media = await media_service.get_media(GetMediaQuery(media_id=command.media_id))

        if not media:
            return create_error_response("Media not found", "Invalid media ID")

        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")

        if getattr(media, "status", None) == "PROCESSING" and not command.force:
            return create_error_response("Media is currently being processed", "Cannot reprocess")

        # The command for transcription_service.reprocess_transcription already has all necessary data
        # It relies on media.original_file_path and media.storage_provider
        # Need to ensure ReprocessTranscriptionCommand DTO is sufficient
        # Or MediaProcessingService should fetch media if needed.
        # For now, pass all necessary data to the command.
        command.user_id = current_user.id # Add user_id to command for auth/ownership check in service if needed
        
        result = await transcription_service.reprocess_transcription(command)

        response_data = {
            "reprocessing": {
                "media_id": str(command.media_id),
                "task_id": result.get("task_id"),
                "provider": command.provider,
                "language": command.language,
                "status": "SCHEDULED",
            },
            "message": "Transcription reprocessing started. Check WebSocket for real-time updates.",
        }

        return create_success_response(
            data=response_data,
            message="Transcription reprocessing initiated",
        )

    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing",
        )