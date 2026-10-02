"""FastAPI routers exposing text analysis operations."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

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
from src.shared.domain.errors import AccessDeniedError, NotFoundError
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from .dependencies import AnalyzeRequest, AnalyzeResponse, get_text_analysis_service, get_knowledge_service

logger = get_logger(__name__)

router = APIRouter(prefix="/text-analysis", tags=["text-analysis"])


@router.get("/search")
async def semantic_search(
    query: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=20),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    """Busca semântica nas mídias do usuário (administradores veem todas)."""
    owner_filter = None if current_user.role == UserRole.ADMIN else current_user.id
    return await service.search(query, limit=limit, user_id=owner_filter)


def _ensure_owner(owner, current_user: User) -> None:
    """Só o dono (ou um administrador) vê ou altera a análise."""
    if owner and str(owner) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise AccessDeniedError("Acesso negado")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    payload: AnalyzeRequest,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    media_read_service: MediaReadService = Depends(get_media_read_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    if payload.media_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe um media_id para análise")
    media = await media_read_service.get_media(GetMediaQuery(media_id=payload.media_id))
    if not media:
        raise NotFoundError("Mídia não encontrada")
    _ensure_owner(media.user_id, current_user)

    command = AnalyzeTextCommand(
        media_id=payload.media_id,
        document_id=payload.transcription_id or payload.media_id,
        text_content=payload.text or "",
        user_id=current_user.id if current_user else None,
        transcription_id=payload.transcription_id,
        language=payload.language,
    )
    return await service.analyze_text_content(command)


@router.get("/media/{media_id}", response_model=AnalyzeResponse)
async def get_analysis_by_media(
    media_id: UUID,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """Retrieve the latest text analysis result for a given media ID."""
    result = await service.get_analysis_by_media_id(GetAnalysisByMediaIdQuery(media_id=media_id))
    if not result:
        raise NotFoundError("Análise não encontrada para esta mídia")
    _ensure_owner(result.get("user_id"), current_user)
    return result


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis_result(
    analysis_id: UUID,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    result = await service.get_analysis(GetAnalysisQuery(analysis_id=analysis_id))
    _ensure_owner(result.get("user_id"), current_user)
    return result


class SummaryCorrection(BaseModel):
    summary: str = Field(..., min_length=1, description="Resumo corrigido (Markdown).")


async def _ensure_analysis_owner(
    analysis_id: str, service: TextAnalysisService, current_user: User
) -> None:
    """Garante que a análise existe (NotFoundError) e pertence ao usuário."""
    result = await service.get_analysis(GetAnalysisQuery(analysis_id=UUID(str(analysis_id))))
    _ensure_owner(result.get("user_id"), current_user)


@router.post("/{analysis_id}/feedback")
async def submit_analysis_feedback(
    analysis_id: str,
    score: int = Query(..., ge=-1, le=5),
    comment: Optional[str] = Query(None),
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: User = Depends(get_current_user),
):
    """Registra a avaliação humana de uma análise."""
    await _ensure_analysis_owner(analysis_id, service, current_user)
    await service.submit_feedback(analysis_id, current_user.id, score, comment)
    return {"message": "Feedback registrado com sucesso"}


@router.put("/{analysis_id}/summary")
async def correct_analysis_summary(
    analysis_id: str,
    body: Optional[SummaryCorrection] = Body(None),
    new_summary: Optional[str] = Query(
        None, description="Obsoleto: use o corpo JSON {\"summary\": ...}."
    ),
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: User = Depends(get_current_user),
):
    """Corrige o resumo gerado pela IA, preservando o original.

    O texto vai no corpo da requisição: resumos longos em Markdown podem
    ultrapassar o limite de tamanho de uma URL.
    """
    summary = body.summary if body else new_summary
    if not summary:
        raise HTTPException(status_code=422, detail="Informe o resumo corrigido.")
    await _ensure_analysis_owner(analysis_id, service, current_user)
    success = await service.correct_summary(analysis_id, summary)
    if not success:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return {"message": "Resumo atualizado com sucesso"}


@router.get("/{analysis_id}/topics")
async def get_topics(
    analysis_id: UUID,
    service: TextAnalysisService = Depends(get_text_analysis_service),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    analysis = await service.get_analysis(GetAnalysisQuery(analysis_id=analysis_id))
    _ensure_owner(analysis.get("user_id"), current_user)
    return analysis.get("topics", [])


__all__ = ["router"]
