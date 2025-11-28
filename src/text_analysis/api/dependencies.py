"""FastAPI dependency helpers for text analysis."""

from __future__ import annotations

from .schemas import AnalyzeRequest
from ..application import TextAnalysisService


def get_text_analysis_service() -> TextAnalysisService:
    raise RuntimeError("TextAnalysisService dependency not bound")


__all__ = ["get_text_analysis_service", "AnalyzeRequest"]
