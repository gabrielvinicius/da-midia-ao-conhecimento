# src/transcription/api/routers.py
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

# Import dependencies from the local module file and other specific modules
from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_transcription_queries, get_media_queries
from src.summarization.api.dependencies import get_summarization_service # Cross-context dependency

from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.summarization.application.summarization_service import SummarizationService
from .schemas import TranscriptionResponse

router = APIRouter(prefix="/transcriptions", tags=["Transcriptions"])


@router.get("/{transcription_id}", response_model=TranscriptionResponse, summary="Get a transcription by its ID")
async def get_transcription_by_id(
    transcription_id: str,
    queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a transcription by its ID. Requires authentication."""
    transcription = await queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    # Authorization check: Ensure the user owns the media associated with the transcription
    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this transcription")

    return transcription


@router.post("/{transcription_id}/summarization", status_code=status.HTTP_202_ACCEPTED, summary="Request a summary for a transcription")
async def request_summary_for_transcription(
    transcription_id: str,
    provider: Optional[str] = Query("huggingface", description="The summarization provider to use."),
    transcription_queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    summarization_service: SummarizationService = Depends(get_summarization_service),
    current_user: User = Depends(get_current_user),
):
    """Triggers an asynchronous summarization process for a given transcription."""
    transcription = await transcription_queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    # Authorization check
    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to request a summary for this transcription")

    # The service expects media_id, not transcription_id
    await summarization_service.request_summary(
        media_id=str(transcription.media_id),
        provider=provider,
    )

    return {"message": "Summarization requested successfully"}
