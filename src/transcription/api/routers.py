# src/transcription/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional

from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema
from src.auth.domain.user import User
from .dependencies import get_transcription_queries, get_media_queries, get_set_speaker_aliases_handler

from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.transcription.application.commands.commands import SetSpeakerAliasesCommand
from src.transcription.application.commands.handlers import SetSpeakerAliasesCommandHandler
from .schemas import TranscriptionResponse, SpeakerAliasesUpdateRequest
router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])

# Import transcription service for processing
from ..application.services.fastwhisper_service import fastwhisper_service


@router.put("/{transcription_id}/speaker-aliases", response_model=TranscriptionResponse, summary="Set Speaker Aliases for a Transcription")
async def set_speaker_aliases(
    transcription_id: UUID,
    request: SpeakerAliasesUpdateRequest,
    handler: SetSpeakerAliasesCommandHandler = Depends(get_set_speaker_aliases_handler),
    queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Endpoint to set or update the speaker aliases for a given transcription."""
    transcription = await queries.get_by_id(str(transcription_id))
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this transcription")

    command = SetSpeakerAliasesCommand(transcription_id=transcription_id, aliases=request.aliases)
    updated_transcription = await handler.handle(command)
    return updated_transcription


@router.get("/", response_model=TranscriptionResponse, summary="Get a transcription by its Media ID")
async def get_transcription_by_media_id(
    media_id: UUID,
    queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's transcription")
    transcription = await queries.get_by_media_id(str(media_id))
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found for the given media ID")
    return transcription

@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Get a transcription by its ID")
async def get_transcription_by_id(
    transcription_id: str,
    queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    transcription = await queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")
    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transcription")
    return transcription


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess transcription")
async def reprocess_transcription(
    media_id: str = Form(..., description="Media ID to reprocess"),
    provider: Optional[str] = Form(None, description="Provider to use (fastwhisper, whisper, etc.)"),
    language: str = Form("auto", description="Language code"),
    force: bool = Form(False, description="Force reprocessing even if already completed"),
    current_user: User = Depends(get_current_user)
):
    """
    Reprocess transcription for existing media
    Useful for: changing providers, languages, or fixing failed transcriptions
    """
    try:
        # Validate media exists and user has access
        media_queries = get_media_queries()
        media = await media_queries.get_by_id(media_id)
        
        if not media:
            return create_error_response("Media not found", "Invalid media ID")
        
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        
        # Check if reprocessing is allowed
        if media.status == "PROCESSING" and not force:
            return create_error_response("Media is currently being processed", "Cannot reprocess")
        
        # Trigger reprocessing via Celery task
        from src.transcription.tasks.tasks import process_transcription_task
        
        task_result = process_transcription_task.delay(
            media_id=media_id,
            file_path=media.original_file_path,
            storage_provider=media.storage_provider,
            transcription_provider=provider or media.transcription_provider or "fastwhisper",
            language=language
        )
        
        # Update media status
        media.status = "PROCESSING"
        media.transcription_provider = provider or media.transcription_provider
        media.language = language
        
        response_data = {
            "reprocessing": {
                "media_id": media_id,
                "task_id": task_result.id,
                "provider": provider or media.transcription_provider or "fastwhisper",
                "language": language,
                "status": "PROCESSING"
            },
            "message": "Transcription reprocessing started. Check WebSocket for real-time updates."
        }
        
        return create_success_response(
            data=response_data,
            message="Transcription reprocessing initiated"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Reprocessing failed: {str(e)}",
            message="Failed to initiate reprocessing"
        )
