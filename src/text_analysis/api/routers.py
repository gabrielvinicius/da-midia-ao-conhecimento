"""FastAPI routers exposing text analysis operations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.media_management.api.dependencies import get_media_read_service
from src.media_management.application.dtos import GetMediaQuery
from src.media_management.application.services.media_read_service import MediaReadService
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User, UserRole

from ..application.dtos import (
    AnalyzeTextCommand,
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
)
from ..application.services.text_analysis_service import TextAnalysisService
from ..application.services.knowledge_base_service import KnowledgeBaseService
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from .dependencies import AnalyzeRequest, AnalyzeResponse, get_text_analysis_service, get_knowledge_service

logger = get_logger(__name__)

router = APIRouter(prefix="/text-analysis", tags=["text-analysis"])


@router.get("/search")
async def semantic_search(
    query: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=20),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
):
    """Semantic search across all processed media."""
    try:
        return await service.search(query, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca semântica: {str(exc)}",
        )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    payload: AnalyzeRequest,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    media_read_service: MediaReadService = Depends(get_media_read_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    try:
        if payload.media_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe um media_id para análise",
            )

        media = await media_read_service.get_media(GetMediaQuery(media_id=payload.media_id))
        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mídia não encontrada",
            )
        if current_user and media.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )

        command = AnalyzeTextCommand(
            media_id=payload.media_id,
            document_id=payload.transcription_id or payload.media_id,
            text_content=payload.text or "",
            user_id=current_user.id if current_user else None,
            transcription_id=payload.transcription_id,
            language=payload.language,
        )
        result = await service.analyze_text_content(command)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return result


@router.get("/media/{media_id}", response_model=AnalyzeResponse)
async def get_analysis_by_media(
    media_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Retrieve the latest text analysis result for a given media ID."""
    try:
        result = await service.get_analysis_by_media_id(
            GetAnalysisByMediaIdQuery(media_id=UUID(media_id))
        )
        if not result:
            logger.warning("debug.router.not_found", media_id=media_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análise não encontrada para esta mídia",
            )

        logger.info("debug.router.success", media_id=media_id)
        
        owner = result.get("user_id")
        if (
            owner
            and str(owner) != str(current_user.id)
            and current_user.role != UserRole.ADMIN
        ):
            logger.warning("debug.router.forbidden", media_id=media_id, owner=owner, user=str(current_user.id))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("debug.router.exception", error=str(exc), media_id=media_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis_result(
    analysis_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    try:
        result = await service.get_analysis(
            GetAnalysisQuery(analysis_id=UUID(analysis_id))
        )
        owner = result.get("user_id")
        if (
            owner
            and str(owner) != str(current_user.id)
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/media/{media_id}/estimate")
async def estimate_analysis_cost(
    media_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Predictive Observability: Estimate processing time and hardware risk."""
    try:
        return await service.estimate_cost(UUID(media_id))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível gerar estimativa: {str(exc)}",
        )


@router.post("/{analysis_id}/feedback")
async def submit_analysis_feedback(
    analysis_id: str,
    score: int = Query(..., ge=-1, le=5),
    comment: Optional[str] = Query(None),
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: User = Depends(get_current_user),
):
    """Level 7.0: Submit human feedback for AI analysis."""
    await service.submit_feedback(analysis_id, current_user.id, score, comment)
    return {"message": "Feedback registrado com sucesso"}


@router.put("/{analysis_id}/summary")
async def correct_analysis_summary(
    analysis_id: str,
    new_summary: str = Query(...),
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: User = Depends(get_current_user),
):
    """Level 7.0: Correct an AI-generated summary."""
    success = await service.correct_summary(analysis_id, new_summary)
    if not success:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return {"message": "Resumo atualizado com sucesso"}


@router.get("/{analysis_id}/topics")
async def get_topics(
    analysis_id: str,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    try:
        analysis = await service.get_analysis(
            GetAnalysisQuery(analysis_id=UUID(analysis_id))
        )
        topics = analysis.get("topics", [])
        owner = analysis.get("user_id")
        if (
            owner
            and str(owner) != str(current_user.id)
            and current_user.role != UserRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado",
            )
        return topics
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


__all__ = ["router"]
