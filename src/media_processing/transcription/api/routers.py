from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_processing.transcription.application.queries import TranscriptionQueries
from src.media_processing.transcription.application.transcription_service import (
    TranscriptionService,
)
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import (
    BaseResponseSchema,
    create_error_response,
    create_success_response,
)
from src.user_management.domain.user import User

from .dependencies import (
    get_media_queries,
    get_transcription_queries,
    get_transcription_service,
)
from .schemas import SpeakerAliasesUpdateRequest, TranscriptionResponse

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.put("/{transcription_id}/speaker-aliases", response_model=BaseResponseSchema, summary="Set Speaker Aliases for a Transcription")
async def set_speaker_aliases(
    transcription_id: UUID,
    request: SpeakerAliasesUpdateRequest,
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    current_user: User = Depends(get_current_user),
):
    """Endpoint to set or update the speaker aliases for a given transcription."""
    try:
        result = await transcription_service.set_speaker_aliases(transcription_id, request.aliases)
        return create_success_response(data=result, message="Speaker aliases set successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=TranscriptionResponse, summary="Get a transcription by its Media ID")
async def get_transcription_by_media_id(
    media_id: UUID,
    transcription_queries: Annotated[TranscriptionQueries, Depends(get_transcription_queries)],
    current_user: User = Depends(get_current_user),
):
    transcription = await transcription_queries.get_by_media_id(media_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found for the given media ID")
    return transcription


@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Get a transcription by its ID")
async def get_transcription_by_id(
    transcription_id: UUID,
    transcription_queries: Annotated[TranscriptionQueries, Depends(get_transcription_queries)],
    current_user: User = Depends(get_current_user),
):
    transcription = await transcription_queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
    return transcription


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess transcription")
async def reprocess_transcription(
    transcription_service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    media_queries: Annotated[MediaQueries, Depends(get_media_queries)],
    media_id: UUID = Form(..., description="Media ID to reprocess"),
    provider: Optional[str] = Form(None, description="Provider to use"),
    language: str = Form("auto", description="Language code"),
    force: bool = Form(False, description="Force reprocessing even if already completed"),
    current_user: User = Depends(get_current_user),
):
    """Reprocess transcription for existing media
    Useful for: changing providers, languages, or fixing failed transcriptions
    """
    try:
        media = await media_queries.get_by_id(str(media_id))

        if not media:
            return create_error_response("Media not found", "Invalid media ID")

        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")

        if getattr(media, "status", None) == "PROCESSING" and not force:
            return create_error_response("Media is currently being processed", "Cannot reprocess")

        result = await transcription_service.request_transcription_generation(
            media_id=media_id,
            file_path=media.original_file_path,
            storage_provider=media.storage_provider,
            transcription_provider=provider or getattr(media, "transcription_provider", "fastwhisper"),
            language=language,
        )

        response_data = {
            "reprocessing": {
                "media_id": str(media_id),
                "task_id": result.get("task_id"),
                "provider": provider or getattr(media, "transcription_provider", "fastwhisper"),
                "language": language,
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
