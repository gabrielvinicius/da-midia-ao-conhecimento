"""FastAPI router exposing sentiment analysis operations."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.user_management.domain.user import User
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_processing.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.media_processing.transcription.application.queries import TranscriptionQueries
from src.media_processing.transcription.domain.transcription import TranscriptionStatus
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import create_error_response
from src.text_analysis.sentiment_analysis.api.dependencies import (
    get_media_queries,
    get_sentiment_analysis_service,
    get_sentiment_analysis_queries,
)
from src.text_analysis.sentiment_analysis.api.schemas import (
    SentimentAnalysisAck,
    SentimentAnalysisAcceptedResponse,
    SentimentAnalysisResponse,
)
from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.sentiment_analysis.application.queries.sentiment_analysis_queries import (
    SentimentAnalysisQueries,
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


def _get_transcription_queries(
    deps: TranscriptionDependencies = Depends(get_transcription_dependencies),
) -> TranscriptionQueries:
    return deps.queries


@router.post("/analyze", response_model=SentimentAnalysisAcceptedResponse)
async def analyze_sentiment(
    transcription_id: str = Form(..., description="Identifier of the completed transcription."),
    provider: str = Form("huggingface"),
    model: Optional[str] = Form(None),
    *,
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_analysis_service),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(_get_transcription_queries),
    current_user: User = Depends(get_current_user),
):
    """Trigger sentiment analysis for a transcription owned by the current user."""

    transcription = await transcription_queries.get_by_id(transcription_id)
    if not transcription:
        return create_error_response(
            error="Transcription not found",
            message="Invalid transcription identifier",
        )

    if getattr(transcription, "status", None) != TranscriptionStatus.COMPLETED:
        return create_error_response(
            error="Transcription not completed",
            message="Transcription must be completed before analysis",
        )

    text_content = (getattr(transcription, "text", "") or "").strip()
    if len(text_content) < 10:
        return create_error_response(
            error="Transcription text too short",
            message="Provide a transcription with at least 10 characters",
        )

    media_id = getattr(transcription, "media_id", None)
    if media_id:
        media = await media_queries.get_by_id(str(media_id))
        if not media:
            return create_error_response(
                error="Media not found",
                message="Associated media could not be retrieved",
            )
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response(
                error="Not authorized",
                message="Access denied",
            )

    try:
        payload = await sentiment_service.analyze_sentiment(
            transcription_id=transcription_id,
            text=text_content,
            provider=provider,
            model=model,
            media_id=str(media_id) if media_id else None,
            language=None,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return create_error_response(
            error=f"Sentiment analysis failed: {exc}",
            message="Internal sentiment analysis error",
        )

    payload_dict = payload if isinstance(payload, dict) else {}
    ack = SentimentAnalysisAck(
        transcription_id=transcription_id,
        provider=payload_dict.get("provider", provider),
        model=payload_dict.get("model", model),
        task_id=payload_dict.get("task_id"),
    )
    return SentimentAnalysisAcceptedResponse(
        message="Sentiment analysis task scheduled successfully.",
        analysis=ack,
    )


@router.post("/reprocess", response_model=SentimentAnalysisAcceptedResponse)
async def reprocess_sentiment_analysis(
    transcription_id: str = Form(..., description="Transcription to reprocess"),
    provider: str = Form("huggingface"),
    model: Optional[str] = Form(None),
    force: bool = Form(False),
    *,
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_analysis_service),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(_get_transcription_queries),
    current_user: User = Depends(get_current_user),
):
    """Force the regeneration of a sentiment analysis result."""

    transcription = await transcription_queries.get_by_id(transcription_id)
    if not transcription:
        return create_error_response(
            error="Transcription not found",
            message="Invalid transcription identifier",
        )

    text_content = (getattr(transcription, "text", "") or "").strip()
    if len(text_content) < 10:
        return create_error_response(
            error="Transcription text too short",
            message="Provide a transcription with at least 10 characters",
        )

    media_id = getattr(transcription, "media_id", None)
    if media_id:
        media = await media_queries.get_by_id(str(media_id))
        if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
            return create_error_response(
                error="Not authorized",
                message="Access denied",
            )

    try:
        payload = await sentiment_service.analyze_sentiment(
            transcription_id=transcription_id,
            text=text_content,
            provider=provider,
            model=model,
            media_id=str(media_id) if media_id else None,
            language=None,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return create_error_response(
            error=f"Sentiment analysis reprocessing failed: {exc}",
            message="Internal reprocessing error",
        )

    payload_dict = payload if isinstance(payload, dict) else {}
    ack = SentimentAnalysisAck(
        transcription_id=transcription_id,
        provider=payload_dict.get("provider", provider),
        model=payload_dict.get("model", model),
        task_id=payload_dict.get("task_id"),
    )
    return SentimentAnalysisAcceptedResponse(
        message="Sentiment analysis task scheduled successfully.",
        analysis=ack,
    )


__all__ = ["router"]
