"""Dependências da API da análise.

Ligadas por bootstrap.bind_text_analysis_module à montagem única do módulo.
"""

from __future__ import annotations

from ..application.services.analysis_request_service import AnalysisRequestService
from ..application.services.analysis_review_service import AnalysisReviewService
from ..application.services.knowledge_base_service import KnowledgeBaseService
from ..application.services.text_analysis_read_service import TextAnalysisReadService


def get_analysis_read_service() -> TextAnalysisReadService:
    raise NotImplementedError("TextAnalysisReadService não configurado (bind_text_analysis_module).")


def get_analysis_review_service() -> AnalysisReviewService:
    raise NotImplementedError("AnalysisReviewService não configurado (bind_text_analysis_module).")


def get_analysis_request_service() -> AnalysisRequestService:
    raise NotImplementedError("AnalysisRequestService não configurado (bind_text_analysis_module).")


def get_knowledge_service() -> KnowledgeBaseService:
    raise NotImplementedError("KnowledgeBaseService não configurado (bind_text_analysis_module).")


__all__ = [
    "get_analysis_read_service",
    "get_analysis_request_service",
    "get_analysis_review_service",
    "get_knowledge_service",
]
