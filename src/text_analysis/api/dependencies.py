"""FastAPI dependency helpers for text analysis.

Ligadas por bootstrap.bind_text_analysis_module à montagem única do módulo.
"""

from __future__ import annotations

from ..application import TextAnalysisService
from ..application.services.knowledge_base_service import KnowledgeBaseService
from .schemas import AnalyzeRequest, AnalyzeResponse


def get_text_analysis_service() -> TextAnalysisService:
    """Returns the TextAnalysisService instance."""
    raise NotImplementedError("TextAnalysisService not configured.")


def get_knowledge_service() -> KnowledgeBaseService:
    """Returns the KnowledgeBaseService instance."""
    raise NotImplementedError("KnowledgeBaseService not configured.")


__all__ = ["get_text_analysis_service", "get_knowledge_service", "AnalyzeRequest", "AnalyzeResponse"]
