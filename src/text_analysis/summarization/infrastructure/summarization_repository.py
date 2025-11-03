"""Compatibility wrapper exposing the ORM summarization repository."""

from src.text_analysis.summarization.infrastructure.orm.summarization_repository import (
    SummarizationRepository as _SummarizationRepository,
)

SummarizationRepository = _SummarizationRepository
SummaryRepository = _SummarizationRepository

__all__ = ["SummarizationRepository", "SummaryRepository"]
