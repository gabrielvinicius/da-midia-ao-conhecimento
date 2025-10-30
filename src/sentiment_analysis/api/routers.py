"""FastAPI router exposing sentiment analysis operations."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.user_management.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries
from src.sentiment_analysis.api.dependencies import (
    get_analyze_sentiment_command_handler,
    get_media_queries,
    get_sentiment_analysis_queries,
)
from src.sentiment_analysis.api.schemas import SentimentAnalysisResponse
from src.sentiment_analysis.application.commands.analyze_sentiment_command import (
    AnalyzeSentimentCommand,
)
from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import (
    AnalyzeSentimentCommandHandler,
)
from src.sentiment_analysis.application.queries.sentiment_analysis_queries import (
    SentimentAnalysisQueries,
)
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import (
    BaseResponseSchema,
    create_error_response,
    create_success_response,
)

router = APIRouter(prefix="/sentiment-analysis", tags=["Sentiment Analysis"])


@router.get("/", response_model=SentimentAnalysisResponse)
async def get_sentiment_analysis_by_media_id(
    media_id: UUID,
    queries: SentimentAnalysisQueries = Depends(get_sentiment_analysis_queries),
    media_queries: MediaQueries = Depends(get_media_queries),
    current_user: User = Depends(get_current_user),
):
    """Return the latest sentiment analysis associated with a media item."""

    media = await media_queries.get_by_id(media_id)
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this media's analysis",
        )

    analysis = await queries.get_by_media_id(str(media_id))
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sentiment analysis result not found for the given media ID.",
        )

    return SentimentAnalysisResponse.from_domain(analysis)


@router.post("/analyze", response_model=BaseResponseSchema)
async def analyze_sentiment(
    transcription_id: str = Form(..., description="Identifier of the completed transcription."),
    provider: str = Form("huggingface"),
    model: Optional[str] = Form(None),
    handler: AnalyzeSentimentCommandHandler = Depends(
        get_analyze_sentiment_command_handler
    ),
    current_user: User = Depends(get_current_user),
):
    """Trigger sentiment analysis for a transcription owned by the current user."""

    command = AnalyzeSentimentCommand(
        transcription_id=transcription_id,
        provider=provider,
        model=model,
    )

    try:
        analysis = await handler.handle(command)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - bubbled domain errors
        return create_error_response(
            error=f"Sentiment analysis failed: {exc}",
            message="Internal sentiment analysis error",
        )

    response = SentimentAnalysisResponse.from_domain(analysis)
    return create_success_response(
        data=response.model_dump(),
        message="Sentiment analysis completed successfully",
    )


@router.post("/reprocess", response_model=BaseResponseSchema)
async def reprocess_sentiment_analysis(
    transcription_id: str = Form(..., description="Transcription to reprocess"),
    provider: str = Form("huggingface"),
    model: Optional[str] = Form(None),
    force: bool = Form(False),
    handler: AnalyzeSentimentCommandHandler = Depends(
        get_analyze_sentiment_command_handler
    ),
    current_user: User = Depends(get_current_user),
):
    """Force the regeneration of a sentiment analysis result."""

    command = AnalyzeSentimentCommand(
        transcription_id=transcription_id,
        provider=provider,
        model=model,
    )

    try:
        analysis = await handler.handle(command)
    except Exception as exc:  # pragma: no cover - defensive
        return create_error_response(
            error=f"Sentiment analysis reprocessing failed: {exc}",
            message="Internal reprocessing error",
        )

    response = SentimentAnalysisResponse.from_domain(analysis)
    return create_success_response(
        data=response.model_dump(),
        message="Sentiment analysis reprocessing completed",
    )


__all__ = ["router"]

