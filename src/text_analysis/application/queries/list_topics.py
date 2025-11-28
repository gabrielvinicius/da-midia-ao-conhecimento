"""Query handler for listing topics of an analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ...domain.errors import DomainError
from ...domain.value_objects import Topic
from ..ports import AnalysisRepositoryPort


@dataclass(slots=True)
class ListTopicsQuery:
    analysis_id: str


class ListTopicsQueryHandler:
    def __init__(self, repository: AnalysisRepositoryPort) -> None:
        self.repository = repository

    def __call__(self, query: ListTopicsQuery) -> List[Topic]:
        topics = self.repository.list_topics(query.analysis_id)
        if topics is None:
            raise DomainError(f"Analysis {query.analysis_id} not found")
        return topics

