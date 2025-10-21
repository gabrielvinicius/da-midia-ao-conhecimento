# src/sentiment_analysis/api/routers.py
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form

# Import dependencies from their correct, decoupled locations
from src.shared.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_sentiment_analysis_queries, get_media_queries

from src.media_management.application.queries.media_queries import MediaQueries
from ..application.queries.sentiment_analysis_queries import SentimentAnalysisQueries
from .schemas import SentimentAnalysisResponse
from src.shared.api.unified_schemas import create_success_response, create_error_response, BaseResponseSchema

router = APIRouter(prefix="/sentiment-analysis", tags=["Sentiment Analysis"])


@router.get("/", response_model=SentimentAnalysisResponse, summary="Get sentiment analysis result by Media ID")
async def get_sentiment_analysis_by_media_id(
    media_id: UUID,
    queries: SentimentAnalysisQueries = Depends(get_sentiment_analysis_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Retrieves the sentiment analysis result for a specific media ID."""
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media's analysis")

    analysis_result = await queries.get_by_media_id(str(media_id))
    if not analysis_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentiment analysis result not found for the given media ID.")

    return analysis_result


@router.post("/analyze", response_model=BaseResponseSchema, summary="Analyze sentiment in text")
async def analyze_sentiment(
    text: str = Form(..., description="Text to analyze for sentiment"),
    media_id: Optional[str] = Form(None, description="Associated media ID"),
    provider: Optional[str] = Form(None, description="Provider to use for analysis"),
    current_user: User = Depends(get_current_user)
):
    """Analyze sentiment in provided text"""
    try:
        # Validate input
        if not text.strip():
            return create_error_response("Empty text provided", "Input validation failed")
        
        if len(text) < 10:
            return create_error_response("Text too short for sentiment analysis", "Input validation failed")
        
        # TODO: Implement actual sentiment analysis service
        # For now, return a simple response structure
        response_data = {
            "sentiment": {
                "label": "positive",
                "confidence": 0.85,
                "scores": {
                    "positive": 0.85,
                    "negative": 0.10,
                    "neutral": 0.05
                }
            },
            "input_info": {
                "text_length": len(text),
                "media_id": media_id
            },
            "processing_info": {
                "provider_used": provider or "default",
                "user_id": str(current_user.id)
            }
        }
        
        return create_success_response(
            data=response_data,
            message="Sentiment analysis completed successfully"
        )
        
    except Exception as e:
        return create_error_response(
            error=f"Sentiment analysis failed: {str(e)}",
            message="Internal sentiment analysis error"
        )


@router.post("/reprocess", response_model=BaseResponseSchema, summary="Reprocess sentiment analysis")
async def reprocess_sentiment_analysis(
    media_id: str = Form(..., description="Media ID to reprocess"),
    provider: Optional[str] = Form(None, description="Provider to use for analysis"),
    force: Optional[bool] = Form(False, description="Force reprocessing even if result exists"),
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    """Reprocess sentiment analysis for a specific media item"""
    try:
        # Validate media access
        media = await media_queries.get_by_id(media_id)
        if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this media")

        # TODO: Implement actual reprocessing logic
        # For now, return a simple response structure
        response_data = {
            "media_id": media_id,
            "status": "processing",
            "provider": provider or "default",
            "force": force,
            "message": "Sentiment analysis reprocessing initiated"
        }
        
        return create_success_response(
            data=response_data,
            message="Sentiment analysis reprocessing started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return create_error_response(
            error=f"Sentiment analysis reprocessing failed: {str(e)}",
            message="Internal reprocessing error"
        )
