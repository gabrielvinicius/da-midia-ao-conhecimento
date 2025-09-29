# src/summarization/api/routers.py
from fastapi import APIRouter, Depends, HTTPException, status

# Import dependencies from the local module file and other specific modules
from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_summary_queries, get_media_queries

from src.summarization.application.queries.summary_queries import SummaryQueries
from src.media_management.application.queries.media_queries import MediaQueries
from .schemas import SummaryResponse

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.get("/{summary_id}", response_model=SummaryResponse, summary="Get a summary by its ID")
async def get_summary_by_id(
    summary_id: str, 
    queries: SummaryQueries = Depends(get_summary_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a summary by its ID. Requires authentication."""
    summary = await queries.get_by_id(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # Authorization check: Ensure the user owns the media associated with the summary
    media = await media_queries.get_by_id(str(summary.media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this summary")

    return summary
