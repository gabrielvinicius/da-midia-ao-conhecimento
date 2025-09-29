# src/summarization/api/routers.py
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

# Import dependencies from the local module file and other specific modules
from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summarization_service, get_summary_queries, get_media_queries, get_transcription_queries

from src.summarization.application.summarization_service import SummarizationService
from src.summarization.application.queries.summary_queries import SummaryQueries
from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from .schemas import SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.post(
    "/from-transcription/{transcription_id}", 
    status_code=status.HTTP_202_ACCEPTED, 
    summary="Request a new summary from a transcription"
)
async def request_summary_for_transcription(
    transcription_id: str,
    provider: Optional[str] = Query("huggingface", description="The summarization provider to use."),
    transcription_queries: TranscriptionQueries = Depends(get_transcription_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    summarization_service: SummarizationService = Depends(get_summarization_service),
    current_user: User = Depends(get_current_user),
):
    """Triggers an asynchronous summarization process for a given transcription ID."""
    transcription = await transcription_queries.get_by_id(transcription_id)
    if not transcription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found")

    # Authorization check
    media = await media_queries.get_by_id(str(transcription.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to request a summary for this media")

    await summarization_service.request_summary(
        media_id=str(transcription.media_id),
        provider=provider,
    )

    return {"message": "Summarization request accepted"}


@router.get(
    "/{summary_id}", 
    response_model=SummaryResponse, 
    summary="Get a summary by its ID",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not authorized to access this summary"},
        404: {"description": "Summary not found"},
    }
)
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a summary by its ID. Requires authentication."""
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    # Authorization check
    media = await media_queries.get_by_id(str(summary.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")

    return summary
