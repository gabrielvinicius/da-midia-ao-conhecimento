"""Rotas da análise: leitura, revisão humana, pedido de análise e busca.

Quem pode ver ou alterar cada análise é decidido na camada de aplicação
(application/access.py); as rotas só traduzem HTTP.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field

from src.shared.infrastructure.middleware.correlation_middleware import correlation_id_of
from src.shared.application.access import Requester
from src.user_management.api.dependencies import get_requester
from ..application.dtos import GetAnalysisByMediaIdQuery, GetAnalysisQuery, ListTopicsQuery
from ..application.services.analysis_request_service import AnalysisRequestService
from ..application.services.analysis_review_service import AnalysisReviewService
from ..application.services.knowledge_base_service import KnowledgeBaseService
from ..application.services.text_analysis_read_service import TextAnalysisReadService
from ..domain.chapters import Chapter, ReviewQuestion
from .dependencies import (
    get_analysis_read_service,
    get_analysis_request_service,
    get_analysis_review_service,
    get_knowledge_service,
)
from .schemas import AnalyzeRequest, AnalyzeResponse, StudyDeckEntryResponse

router = APIRouter(prefix="/text-analysis", tags=["text-analysis"])


@router.get("/search")
async def semantic_search(
    query: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=20),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
    requester: Requester = Depends(get_requester),
):
    """Busca semântica nas mídias do usuário (administradores veem todas)."""
    return await service.search(query, limit=limit, user_id=None if requester.is_admin else requester.user_id)


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def request_analysis(
    payload: AnalyzeRequest,
    request: Request,
    service: AnalysisRequestService = Depends(get_analysis_request_service),
    requester: Requester = Depends(get_requester),
):
    """Pede uma nova análise da mídia ao worker; o resultado chega pelos avisos."""
    await service.request(payload.media_id, requester, correlation_id_of(request))
    return {"media_id": str(payload.media_id), "status": "queued"}


@router.get("/study-deck", response_model=list[StudyDeckEntryResponse], summary="Perguntas de revisão de todas as mídias")
async def study_deck(
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    requester: Requester = Depends(get_requester),
):
    """As perguntas de revisão (com a resposta e o momento da gravação) de todas
    as análises de quem pede, das mais novas para as mais antigas."""
    return [StudyDeckEntryResponse.model_validate(asdict(entry)) for entry in await service.study_deck(requester)]


@router.get("/media/{media_id}", response_model=AnalyzeResponse)
async def get_analysis_by_media(
    media_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    requester: Requester = Depends(get_requester),
):
    return await service.get_analysis_by_media_id(
        GetAnalysisByMediaIdQuery(media_id=media_id), requester
    )


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis_result(
    analysis_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    requester: Requester = Depends(get_requester),
):
    return await service.get_analysis(GetAnalysisQuery(analysis_id=analysis_id), requester)


@router.get("/{analysis_id}/topics")
async def get_topics(
    analysis_id: UUID,
    service: TextAnalysisReadService = Depends(get_analysis_read_service),
    requester: Requester = Depends(get_requester),
):
    return await service.list_topics(ListTopicsQuery(analysis_id=analysis_id), requester)


class FeedbackRequest(BaseModel):
    score: int = Field(..., ge=-1, le=5, description="-1 (não útil), 1 (útil) ou nota de 1 a 5.")
    comment: Optional[str] = Field(None, max_length=2000)


@router.post("/{analysis_id}/feedback")
async def submit_analysis_feedback(
    analysis_id: UUID,
    body: FeedbackRequest,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    requester: Requester = Depends(get_requester),
):
    """Registra a avaliação humana de uma análise (no corpo, não na URL)."""
    await service.submit_feedback(analysis_id, requester, body.score, body.comment)
    return {"message": "Avaliação registrada."}


class SummaryCorrection(BaseModel):
    summary: str = Field(..., min_length=1, description="Resumo corrigido (Markdown).")


@router.put("/{analysis_id}/summary")
async def correct_analysis_summary(
    analysis_id: UUID,
    body: SummaryCorrection,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    requester: Requester = Depends(get_requester),
):
    """Corrige o resumo gerado pela IA, preservando o original."""
    await service.correct_summary(analysis_id, requester, body.summary)
    return {"message": "Resumo atualizado."}


class TopicTitleCorrection(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.put("/{analysis_id}/topics/{topic_id}")
async def rename_topic(
    analysis_id: UUID,
    topic_id: int,
    body: TopicTitleCorrection,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    requester: Requester = Depends(get_requester),
):
    """Corrige o título de um tema, preservando o dado pela IA."""
    await service.rename_topic(analysis_id, requester, topic_id, body.title)
    return {"message": "Tema atualizado."}


class ChapterIn(BaseModel):
    start: float = Field(..., ge=0)
    end: float = Field(..., ge=0)
    title: str = Field(..., min_length=1, max_length=200)


class ReviewQuestionIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    answer: str = Field(..., min_length=1, max_length=2000)
    start: Optional[float] = Field(None, ge=0)


class StudyAidsCorrection(BaseModel):
    chapters: list[ChapterIn] = Field(default_factory=list, max_length=50)
    review_questions: list[ReviewQuestionIn] = Field(default_factory=list, max_length=50)


@router.put("/{analysis_id}/study")
async def correct_study_aids(
    analysis_id: UUID,
    body: StudyAidsCorrection,
    service: AnalysisReviewService = Depends(get_analysis_review_service),
    requester: Requester = Depends(get_requester),
):
    """Corrige capítulos e perguntas de revisão, preservando a versão da IA."""
    await service.correct_study_aids(
        analysis_id,
        requester,
        [Chapter(start=c.start, end=c.end, title=c.title.strip()) for c in body.chapters],
        [
            ReviewQuestion(question=q.question.strip(), answer=q.answer.strip(), start=q.start)
            for q in body.review_questions
        ],
    )
    return {"message": "Capítulos e perguntas atualizados."}


__all__ = ["router"]
