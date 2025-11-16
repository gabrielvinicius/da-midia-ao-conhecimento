"""Unified FastAPI router for the text analysis bounded context."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.media_management.api.dependencies import get_media_queries
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_processing.transcription.api.dependencies import (
    TranscriptionDependencies,
    get_transcription_dependencies,
)
from src.media_processing.transcription.application.queries.transcription_queries import (
    TranscriptionQueries,
)
from src.media_processing.transcription.domain.transcription import TranscriptionStatus
from src.shared.api.dependencies import get_current_user
from src.shared.api.unified_schemas import create_error_response
from src.text_analysis.sentiment_analysis.api.dependencies import (
    get_sentiment_analysis_repository,
    get_sentiment_analysis_service,
)
from src.text_analysis.sentiment_analysis.api.schemas import (
    SentimentAnalysisAcceptedResponse,
    SentimentAnalysisAck,
    SentimentAnalysisResponse,
)
from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.text_analysis.summarization.api.dependencies import (
    get_summarization_repository,
    get_summarization_service,
)
from src.text_analysis.summarization.api.schemas import (
    SummaryReprocessAck,
    SummaryReprocessResponse,
    SummaryResponse,
)
from src.text_analysis.summarization.application.summarization_service import (
    SummarizationService,
)
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.topic_modeling.api.dependencies import (
    get_topic_modeling_repository,
    get_topic_modeling_service,
)
from src.text_analysis.topic_modeling.api.schemas import (
    TopicModelingAcceptedResponse,
    TopicModelingAck,
    TopicModelingResponse,
)
from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)
from src.user_management.domain.user import User

router = APIRouter()


def _get_transcription_queries(
    deps: TranscriptionDependencies = Depends(get_transcription_dependencies),
) -> TranscriptionQueries:
    return deps.queries


@router.get(
    "/summaries/",
    response_model=SummaryResponse,
    summary="Get a summary by its Media ID",
)
async def get_summary_by_media_id(
    media_id: UUID,
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    repository: SummarizationRepository = Depends(get_summarization_repository),
):
    """Return the most recent summary for the supplied media."""
    media = await media_queries.get_by_id(str(media_id))
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    summary = await repository.get_by_media_id(media_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found for the given media ID",
        )

    return SummaryResponse.from_domain(summary)


@router.get(
    "/summaries/{summary_id}",
    response_model=SummaryResponse,
    summary="Get a summary by its ID",
)
async def get_summary_by_id(
    summary_id: UUID,
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    repository: SummarizationRepository = Depends(get_summarization_repository),
):
    """Return a summary aggregate by its identifier."""
    summary = await repository.get_by_id(summary_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    media = await media_queries.get_by_id(str(summary.media_id))
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return SummaryResponse.from_domain(summary)


@router.post(
    "/summaries/reprocess",
    response_model=SummaryReprocessResponse,
    summary="Reprocess summarization",
)
async def reprocess_summarization(
    media_id: UUID = Form(..., description="Media ID to reprocess summary"),
    provider: Optional[str] = Form(None, description="Provider to use for summarization"),
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(_get_transcription_queries),
    summarization_service: SummarizationService = Depends(get_summarization_service),
):
    """Schedule a new summarisation task for an existing media item."""
    media = await media_queries.get_by_id(str(media_id))
    if media is None:
        return create_error_response("Media not found", "Invalid media ID")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        return create_error_response("Not authorized", "Access denied")

    transcription = await transcription_queries.get_by_media_id(str(media_id))
    if transcription is None or not getattr(transcription, "text", ""):
        return create_error_response("No transcription found", "Transcription required for summarization")

    provider_name = provider or getattr(media, "summarization_provider", None) or "builtin"
    try:
        task_info = await summarization_service.generate_summary(
            media_id=media_id,
            transcription_id=transcription.id,
            text_content=transcription.text,
            provider=provider_name,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return create_error_response(
            error=f"Reprocessing failed: {exc}",
            message="Failed to initiate reprocessing",
        )

    task_id = task_info.get("task_id") if isinstance(task_info, dict) else None
    response_data = SummaryReprocessAck(
        media_id=media_id,
        provider=provider_name,
        task_id=task_id,
    )

    return SummaryReprocessResponse(
        message="Summarization task scheduled successfully.",
        reprocessing=response_data,
    )


@router.get(
    "/sentiment-analysis/",
    response_model=SentimentAnalysisResponse,
    summary="Get sentiment analysis by media ID",
)
async def get_sentiment_analysis_by_media_id(
    media_id: UUID,
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    repository: SentimentAnalysisRepository = Depends(get_sentiment_analysis_repository),
):
    """Return the latest sentiment analysis associated with a media item."""
    media = await media_queries.get_by_id(str(media_id))
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    analysis = await repository.get_by_media_id(str(media_id))
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sentiment analysis result not found for the given media ID.",
        )

    return SentimentAnalysisResponse.from_domain(analysis)


@router.post(
    "/sentiment-analysis/analyze",
    response_model=SentimentAnalysisAcceptedResponse,
    summary="Trigger sentiment analysis",
)
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


@router.post(
    "/sentiment-analysis/reprocess",
    response_model=SentimentAnalysisAcceptedResponse,
    summary="Reprocess sentiment analysis",
)
async def reprocess_sentiment_analysis(
    transcription_id: str = Form(..., description="Transcription to reprocess"),
    provider: str = Form("huggingface"),
    model: Optional[str] = Form(None),
    *,
    sentiment_service: SentimentAnalysisService = Depends(get_sentiment_analysis_service),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(_get_transcription_queries),
    current_user: User = Depends(get_current_user),
):
    """Force regeneration of a sentiment analysis result."""
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


@router.get(
    "/topic-modeling/",
    response_model=TopicModelingResponse,
    summary="Get topic modeling result by media ID",
)
async def get_topic_modeling_result_by_media_id(
    media_id: UUID,
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    topic_repository: TopicModelingRepository = Depends(get_topic_modeling_repository),
    topic_service: TopicModelingService = Depends(get_topic_modeling_service),
):
    """Return the topic modeling result for the provided media."""
    media = await media_queries.get_by_id(str(media_id))
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    analysis_result = await topic_repository.get_by_media_id(media_id)
    if analysis_result is None:
        analysis_result = await topic_service.get_topic_modeling_result(media_id)

    if analysis_result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic modeling result not found for the given media ID.",
        )

    return TopicModelingResponse.from_domain(analysis_result)


@router.post(
    "/topic-modeling/analyze",
    response_model=TopicModelingAcceptedResponse,
    summary="Analyze topics in text",
)
async def analyze_topics(
    text_content: str = Form(..., description="Text to analyze for topics"),
    media_id: Optional[UUID] = Form(None, description="Associated media ID"),
    provider: str = Form("bertopic_placeholder", description="Provider to use for topic modeling"),
    language: str = Form("en", description="Language of the text"),
    options: Optional[dict[str, Any]] = Form(None, description="Additional options for topic modeling"),
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    topic_service: TopicModelingService = Depends(get_topic_modeling_service),
):
    """Analyze topics in the provided text content."""
    if not text_content.strip():
        return create_error_response("Empty text provided", "Input validation failed")

    if len(text_content) < 100:
        return create_error_response("Text too short for topic modeling", "Input validation failed")

    media_uuid_str: Optional[str] = None
    if media_id is not None:
        media = await media_queries.get_by_id(str(media_id))
        if media is None:
            return create_error_response("Media not found", "Invalid media ID")
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            return create_error_response("Not authorized", "Access denied")
        media_uuid_str = str(media_id)

    media_uuid = media_id or UUID(int=0)

    try:
        result = await topic_service.request_topic_analysis(
            media_id=media_uuid,
            text_content=text_content,
            provider=provider,
            language=language,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    task_info = result if isinstance(result, dict) else {}
    ack = TopicModelingAck(
        media_id=media_uuid_str or task_info.get("media_id"),
        provider=task_info.get("provider", provider),
        language=task_info.get("language", language),
        task_id=task_info.get("task_id"),
    )

    return TopicModelingAcceptedResponse(
        message="Topic modeling task scheduled successfully.",
        analysis=ack,
    )


@router.post(
    "/topic-modeling/reprocess",
    response_model=TopicModelingAcceptedResponse,
    summary="Reprocess topic modeling",
)
async def reprocess_topic_modeling(
    media_id: UUID = Form(..., description="Media ID to reprocess topic modeling"),
    provider: Optional[str] = Form(None, description="Provider to use for topic modeling"),
    language: str = Form("en", description="Language of the text"),
    force: bool = Form(False, description="Force reprocessing"),
    *,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(_get_transcription_queries),
    topic_service: TopicModelingService = Depends(get_topic_modeling_service),
):
    """Reprocess topic modeling for existing media."""
    media = await media_queries.get_by_id(str(media_id))
    if media is None:
        return create_error_response("Media not found", "Invalid media ID")
    if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
        return create_error_response("Not authorized", "Access denied")

    transcription = await transcription_queries.get_by_media_id(str(media_id))
    if transcription is None or not getattr(transcription, "text", ""):
        return create_error_response(
            "No transcription found",
            "Transcription required for topic modeling",
        )

    try:
        result = await topic_service.request_topic_analysis(
            media_id=media_id,
            text_content=transcription.text,
            provider=provider or "bertopic_placeholder",
            language=language,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    task_info = result if isinstance(result, dict) else {}
    ack = TopicModelingAck(
        media_id=task_info.get("media_id", str(media_id)),
        provider=task_info.get("provider", provider or "bertopic_placeholder"),
        language=task_info.get("language", language),
        task_id=task_info.get("task_id"),
    )

    return TopicModelingAcceptedResponse(
        message="Topic modeling task scheduled successfully.",
        analysis=ack,
    )


__all__ = ["router"]
