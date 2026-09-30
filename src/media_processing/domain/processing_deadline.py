"""Quando uma transcrição deve ser considerada parada.

Sem esta regra, uma mídia cujo worker morreu no meio da tarefa (falta de
memória, queda de energia) ou travou ficava para sempre "em processamento":
nenhuma exceção chega ao código, então nenhuma falha é registrada, e o
reprocessamento só vale para mídias com falha.

O prazo acompanha o tamanho da gravação e a velocidade real da máquina,
medida nas transcrições anteriores (processing_stats): uma aula de 2 h numa
CPU leva horas, e um áudio de 5 min numa GPU, segundos. Um prazo fixo ou
mataria o primeiro ou demoraria demais a liberar o segundo.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from src.media_processing.domain.entities.transcription import (
    Transcription,
    TranscriptionStatus,
)

MEDIA_DURATION_KEY = "media_duration_seconds"


@dataclass(frozen=True)
class ProcessingDeadlinePolicy:
    # Folga sobre a estimativa: a velocidade varia com o conteúdo e a carga.
    safety_factor: float = 3.0
    minimum_seconds: float = 20 * 60
    maximum_seconds: float = 6 * 3600
    # Sem histórico, supõe que a transcrição leva o tempo da própria gravação
    # (conservador na GPU; próximo do real na CPU).
    fallback_realtime_factor: float = 1.0
    # Documentos, imagens ou mídia cuja duração não pôde ser lida.
    unknown_duration_seconds: float = 60 * 60
    # Tarefa que nunca começou: fila perdida (ex.: Redis reiniciado sem dados).
    queue_seconds: float = 24 * 3600

    def processing_deadline(
        self, media_seconds: Optional[float], realtime_factor: Optional[float]
    ) -> float:
        """Segundos que uma tentativa pode durar antes de ser dada como parada."""
        if not media_seconds or media_seconds <= 0:
            return max(self.minimum_seconds, self.unknown_duration_seconds)
        factor = realtime_factor if realtime_factor and realtime_factor > 0 else self.fallback_realtime_factor
        expected = media_seconds * factor
        return min(self.maximum_seconds, max(self.minimum_seconds, expected * self.safety_factor))

    def deadline_for(
        self, transcription: Transcription, realtime_factor: Optional[float]
    ) -> Optional[float]:
        if transcription.status == TranscriptionStatus.PENDING:
            return self.queue_seconds
        if transcription.status == TranscriptionStatus.PROCESSING:
            media_seconds = (transcription.result or {}).get(MEDIA_DURATION_KEY)
            return self.processing_deadline(media_seconds, realtime_factor)
        return None

    def is_stalled(
        self,
        transcription: Transcription,
        now: datetime.datetime,
        realtime_factor: Optional[float],
    ) -> bool:
        deadline = self.deadline_for(transcription, realtime_factor)
        if deadline is None:
            return False
        # Em processamento, updated_at marca o início da tentativa atual (cada
        # nova tentativa o renova); na fila, conta desde a criação.
        started = (
            transcription.created_at
            if transcription.status == TranscriptionStatus.PENDING
            else transcription.updated_at
        ) or transcription.created_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=datetime.timezone.utc)
        return (now - started).total_seconds() > deadline
