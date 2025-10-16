# src/sentiment_analysis/api/routers.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from src.media_management.api.dependencies import get_media_queries
from src.media_management.application.queries.media_queries import MediaQueries
from .dependencies import get_sentiment_analysis_queries
from .schemas import SentimentAnalysisResponse
from ..application.queries.sentiment_analysis_queries import SentimentAnalysisQueries

router = APIRouter(prefix="/sentiment-analysis", tags=["Sentiment Analysis"])


@router.get("/", response_model=SentimentAnalysisResponse, summary="Get sentiment analysis result by Media ID")
async def get_sentiment_analysis_by_media_id(
    media_id: UUID = Query(..., description="Media ID to get sentiment analysis for"),
    queries: SentimentAnalysisQueries = Depends(get_sentiment_analysis_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the sentiment analysis result for a specific media ID."""
    # Authorization check first: Does the user own the media?
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")

    # Fetch the analysis result
    analysis_result = await queries.get_by_media_id(str(media_id))
    if not analysis_result:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED, 
            detail="Sentiment analysis is being processed. Please check back later."
        )

    return analysis_result
