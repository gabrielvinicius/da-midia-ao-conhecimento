from dataclasses import dataclass
from typing import Optional

from ...domain import Analysis
from ..ports import AnalysisRepositoryPort


@dataclass(frozen=True)
class GetAnalysisByMediaQuery:
    media_id: str


class GetAnalysisByMediaQueryHandler:
    def __init__(self, repository: AnalysisRepositoryPort):
        self.repository = repository

    def __call__(self, query: GetAnalysisByMediaQuery) -> Optional[Analysis]:
        return self.repository.get_by_media_id(query.media_id)
