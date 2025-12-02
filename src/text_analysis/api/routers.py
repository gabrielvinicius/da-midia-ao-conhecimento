"""FastAPI routers exposing text analysis operations."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.media_management.api.dependencies import get_media_queries
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_processing.transcription.api.dependencies import get_transcription_queries
from src.media_processing.transcription.application.queries import TranscriptionQueries
from src.shared.api.dependencies import get_current_user
from src.user_management.domain.user import User

from .dependencies import AnalyzeRequest, AnalyzeResponse, get_text_analysis_service
from ..application.service import TextAnalysisService

router = APIRouter(prefix="/text-analysis", tags=["text-analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    payload: AnalyzeRequest,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    media_queries: MediaQueries = Depends(get_media_queries),
    transcription_queries: TranscriptionQueries = Depends(get_transcription_queries),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    media = None
    if payload.media_id:
        media = await media_queries.get_by_id(payload.media_id)
        if not media:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
        if str(media.user_id) != str(current_user.id) and current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    transcription = None
    transcription_id: Optional[UUID] = payload.transcription_id
    if payload.transcription_id:
        transcription = await transcription_queries.get_by_id(payload.transcription_id)
        if not transcription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcription not found",
            )
    elif payload.media_id:
        transcription = await transcription_queries.get_by_media_id(payload.media_id)
        if transcription:
            transcription_id = transcription.id

    text_source = payload.text or (
        getattr(transcription, "text", None) if transcription else None
    )
    if not text_source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text available for analysis",
        )

    segments = (
        [s.dict() for s in payload.segments]
        if payload.segments
        else getattr(transcription, "segments", None)
    )
    language = payload.language or getattr(transcription, "language", None)

    try:
        result = await service.analyze_text_content(
            media_id=str(payload.media_id) if payload.media_id else None,
            transcription_id=str(transcription_id) if transcription_id else None,
            text_content=text_source,
            segments=segments,
            language=language,
            provider=payload.provider,
            options={
                "chunk_size": payload.chunk_size,
                "chunk_overlap": payload.chunk_overlap,
                "use_transformer_topic_representation": (
                    payload.use_transformer_topic_representation
                ),
                "transformer_representation_model": (
                    payload.transformer_representation_model
                ),
                "llm_model": payload.llm_model,
            },
            user_id=str(current_user.id) if current_user else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis_result(
    analysis_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    try:
        result = service.get_analysis(analysis_id)
        owner = result.get("user_id")
        if owner and str(owner) != str(current_user.id) and current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/media/{media_id}", response_model=AnalyzeResponse)
async def get_analysis_by_media(
    media_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Retrieve the latest text analysis result for a given media ID."""
    try:
        result = service.get_analysis_by_media_id(media_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found for this media")
            
        owner = result.get("user_id")
        if owner and str(owner) != str(current_user.id) and current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{analysis_id}/topics")
async def get_topics(
    analysis_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    try:
        topics = service.list_topics(analysis_id)
        analysis = service.get_analysis(analysis_id)
        owner = analysis.get("user_id")
        if owner and str(owner) != str(current_user.id) and current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return topics
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


__all__ = ["router"]