"""Lista única dos módulos que guardam dados derivados de uma mídia.

Todo ponto de montagem do MediaService usa esta função; antes, cada um montava
a sua lista, e a rota de exclusão da API esquecia a análise. A ordem importa:
a análise primeiro (seus trechos referenciam a mídia), depois a transcrição.
"""
from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.ports import MediaDataEraserPort
from src.media_processing.infrastructure.adapters.transcription_cleanup_adapter import (
    TranscriptionDataEraser,
)
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)
from src.text_analysis.infrastructure.adapters.text_analysis_cleanup_adapter import (
    TextAnalysisDataEraser,
)
from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


def build_media_data_erasers(session: AsyncSession) -> List[MediaDataEraserPort]:
    return [
        TextAnalysisDataEraser(SqlAlchemyAnalysisRepository(session)),
        TranscriptionDataEraser(TranscriptionRepository(db=session)),
    ]


__all__ = ["build_media_data_erasers"]
