# src/summarization/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summary_queries, get_media_queries

from src.summarization.application.queries.summary_queries import SummaryQueries
from src.media_management.application.queries.media_queries import MediaQueries
from .schemas import SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/", response_model=SummaryResponse, summary="Get a summary by its Media ID")
async def get_summary_by_media_id(
    media_id: UUID,
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's summary")
    summary = await queries.get_by_media_id(str(media_id))
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found for the given media ID")
    return summary

@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    media = await media_queries.get_by_id(str(summary.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")
    return summary
