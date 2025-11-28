"""Query for retrieving stored analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ...domain.errors import DomainError
from ..dto import AnalysisResultDTO
from ..mappers import analysis_to_dto
from ..ports import AnalysisRepositoryPort


@dataclass(slots=True)
class GetAnalysisQuery:
    analysis_id: str


class GetAnalysisQueryHandler:
    def __init__(self, repository: AnalysisRepositoryPort) -> None:
        self.repository = repository

    def __call__(self, query: GetAnalysisQuery) -> AnalysisResultDTO:
        analysis = self.repository.get(query.analysis_id)
        if not analysis:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return analysis_to_dto(analysis)

