"""Rotas da análise: leitura, revisão humana, pedido de análise e busca.

Quem pode ver ou alterar cada análise é decidido na camada de aplicação
(application/access.py); as rotas só traduzem HTTP.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field

from src.shared.infrastructure.middleware.correlation_middleware import correlation_id_of
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User

from ..application.access import Requester
from ..application.dtos import GetAnalysisByMediaIdQuery, GetAnalysisQuery, ListTopicsQuery
from ..application.services.analysis_request_service import AnalysisRequestService
from ..application.services.analysis_review_service import AnalysisReviewService
from ..application.services.knowledge_base_service import KnowledgeBaseService
from ..application.services.text_analysis_read_service import TextAnalysisReadService
from .dependencies import (
    get_analysis_read_service,
    get_analysis_request_service,
    get_analysis_review_service,
    get_knowledge_service,
)
from .schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/text-analysis", tags=["text-analysis"])


def _requester(user: User) -> Requester:
    return Requester(user_id=user.id, role=user.role)


@router.get("/search")
async def semantic_search(
    query: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=20),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
    current_user: User = Depends(get_current_user),
):
    """Busca semântica nas mídias do usuário (administradores veem todas)."""
    requester = _requester(current_user)
    return await service.search(query, limit=limit, user_id=None if requester.is_admin else requester.user_id)


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def request_analysis(
    payload: AnalyzeRequest,
    request: Request,
    service: AnalysisRequestService = Depends(get_analysis_request_service),
    current_user: User = Depends(get_current_user),
):
    """Pede uma nova análise da mídia ao worker; o resultado chega pelos avisos."""
    await service.request(payload.media_id, _requester(current_user), correlation_id_of(request))
    return {"media_id": str(payload.media_id), "status": "queued"}


@router.get("/media/{media_id}", response_model=AnalyzeResponse)
async def get_analysis_by_media(
    media_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_analysis_by_media_id(
        GetAnalysisByMediaIdQuery(media_id=media_id), _requester(current_user)
    )


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis_result(
    analysis_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_analysis(GetAnalysisQuery(analysis_id=analysis_id), _requester(current_user))


@router.get("/{analysis_id}/topics")
async def get_topics(
    analysis_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    current_user: User = Depends(get_current_user),
):
    return await service.list_topics(ListTopicsQuery(analysis_id=analysis_id), _requester(current_user))


class FeedbackRequest(BaseModel):
    score: int = Field(..., ge=-1, le=5, description="-1 (não útil), 1 (útil) ou nota de 1 a 5.")
    comment: Optional[str] = Field(None, max_length=2000)


@router.post("/{analysis_id}/feedback")
async def submit_analysis_feedback(
    analysis_id: UUID,
    body: FeedbackRequest,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    current_user: User = Depends(get_current_user),
):
    """Registra a avaliação humana de uma análise (no corpo, não na URL)."""
    await service.submit_feedback(analysis_id, _requester(current_user), body.score, body.comment)
    return {"message": "Avaliação registrada."}


class SummaryCorrection(BaseModel):
    summary: str = Field(..., min_length=1, description="Resumo corrigido (Markdown).")


@router.put("/{analysis_id}/summary")
async def correct_analysis_summary(
    analysis_id: UUID,
    body: SummaryCorrection,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    current_user: User = Depends(get_current_user),
):
    """Corrige o resumo gerado pela IA, preservando o original."""
    await service.correct_summary(analysis_id, _requester(current_user), body.summary)
    return {"message": "Resumo atualizado."}


__all__ = ["router"]
