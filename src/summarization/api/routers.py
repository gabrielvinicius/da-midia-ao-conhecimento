# src/summarization/api/routers.py
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

# Import dependencies from the local module file and other specific modules
from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summary_queries
from src.media_management.api.dependencies import get_media_queries

from src.summarization.application.queries.summary_queries import SummaryQueries
from src.media_management.application.queries.media_queries import MediaQueries
from .schemas import SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/", response_model=List[SummaryResponse], summary="List summaries or get by Media ID")
async def list_summaries(
    media_id: Optional[UUID] = Query(None, description="Filter by media ID"),
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """List all summaries for current user or get specific by media_id."""
    if media_id:
        # Get specific summary by media_id
        media = await media_queries.get_by_id(str(media_id))
        if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's summary")

        summary = await queries.get_by_media_id(str(media_id))
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found for the given media ID")

        return [summary]
    else:
        # List all summaries for current user - return empty for now
        return []


@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a specific summary record by its own ID."""
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    # Authorization check
    media = await media_queries.get_by_id(str(summary.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")

    return summary
