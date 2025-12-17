"""FastAPI dependency helpers for text analysis."""

from __future__ import annotations

from ..application import TextAnalysisService
from .schemas import AnalyzeRequest, AnalyzeResponse


def get_text_analysis_service() -> TextAnalysisService:
    raise RuntimeError("TextAnalysisService dependency not bound")


__all__ = ["get_text_analysis_service", "AnalyzeRequest", "AnalyzeResponse"]
