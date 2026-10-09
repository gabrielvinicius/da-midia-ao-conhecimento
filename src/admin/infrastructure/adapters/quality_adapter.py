"""QualityPort sobre a análise (correções e avaliações) e as transcrições
(trechos corrigidos), cada uma lida pelo próprio módulo."""
from __future__ import annotations

from src.admin.application.ports import TranscriptionQuality
from src.media_processing.infrastructure.repositories.transcription_repository import TranscriptionRepository
from src.text_analysis.application.insights import AnalysisQualityReport
from src.text_analysis.application.services.analysis_review_service import AnalysisReviewService
from src.text_analysis.infrastructure.dependencies.builders import build_analysis_review_service


class QualityAdapter:
    def __init__(self, review: AnalysisReviewService, transcriptions: TranscriptionRepository) -> None:
        self._review = review
        self._transcriptions = transcriptions

    @classmethod
    def for_session(cls, session) -> "QualityAdapter":
        return cls(build_analysis_review_service(session), TranscriptionRepository(db=session))

    async def analysis_quality(self) -> AnalysisQualityReport:
        return await self._review.quality_report()

    async def transcription_quality(self) -> TranscriptionQuality:
        return TranscriptionQuality(*await self._transcriptions.segment_correction_counts())


__all__ = ["QualityAdapter"]
