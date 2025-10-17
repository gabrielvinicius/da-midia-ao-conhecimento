# src/transcription/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_transcription_queries, get_media_queries, get_set_speaker_aliases_handler

from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.transcription.application.commands.commands import SetSpeakerAliasesCommand
from src.transcription.application.commands.handlers import SetSpeakerAliasesCommandHandler
from .schemas import TranscriptionResponse, SpeakerAliasesUpdateRequest

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


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
