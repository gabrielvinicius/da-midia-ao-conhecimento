"""Pedido de (nova) análise de uma mídia pela API.

Antes, a rota rodava a análise inteira dentro do processo da API: carregava
os modelos, disputava a GPU com o worker e prendia a requisição por minutos.
Agora o pedido vai para a fila, como o da transcrição, e o worker o executa.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog

from src.shared.domain.errors import ConflictError

from src.shared.application.access import Requester, ensure_can_access
from ..ports import AnalysisQueuePort, TranscriptionQueryPort

logger = structlog.get_logger(__name__)

TEXT_NOT_READY = "O texto desta mídia ainda não está pronto; a análise começa sozinha quando ficar."


class AnalysisRequestService:
    def __init__(self, sources: TranscriptionQueryPort, queue: AnalysisQueuePort) -> None:
        self._sources = sources
        self._queue = queue

    async def request(self, media_id: UUID, requester: Requester, correlation_id: Optional[str] = None) -> None:
        owner = await self._sources.get_media_owner(media_id)
        ensure_can_access(owner, requester, "Mídia não encontrada")
        source = await self._sources.get_text_source(media_id)
        if source is None or not (source.text or "").strip():
            raise ConflictError(TEXT_NOT_READY)
        # O texto não vai na fila: o worker o lê da transcrição.
        self._queue.request_analysis(
            {
                "media_id": str(media_id),
                "transcription_id": str(source.id),
                "user_id": str(owner),
                "language": source.language,
                "correlation_id": correlation_id,
            }
        )
        logger.info("text_analysis.requested", media_id=str(media_id))


__all__ = ["AnalysisRequestService", "TEXT_NOT_READY"]
