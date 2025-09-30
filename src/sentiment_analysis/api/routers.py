# src/sentiment_analysis/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.api.dependencies import get_media_queries
from src.sentiment_analysis.application.queries.analysis_queries import AnalysisQueries
from src.sentiment_analysis.domain.analysis import AnalysisType
from .dependencies import get_analysis_queries
from .schemas import AnalysisResponse

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.get("/", response_model=AnalysisResponse, summary="Get an analysis by Media ID and Type")
async def get_analysis(
    media_id: UUID = Query(..., description="The ID of the media item to get analysis for."),
    analysis_type: AnalysisType = Query(..., description="The type of analysis to retrieve."),
    queries: AnalysisQueries = Depends(get_analysis_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves a specific analysis result (e.g., SENTIMENT) for a given media ID."""
    # 1. Authorization: Ensure the user owns the media
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")

    # 2. Fetch the analysis
    analysis = await queries.get_by_media_id_and_type(media_id, analysis_type)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{analysis_type.value} analysis not found for the given media ID")

    return analysis
