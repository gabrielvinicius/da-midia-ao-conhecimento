from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.media_processing.domain.transcript_confidence import transcript_confidence
from src.shared.domain.base_entity import BaseEntity
from src.shared.domain.errors import ConflictError, ValidationError
from src.shared.domain.time.clock import utcnow


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class InvalidTranscriptionTransitionError(ConflictError):
    """Mudança de estado fora de ordem: um resultado que chega depois de a
    transcrição ter sido dada como parada, por exemplo."""


# Na fila → em processamento → concluída ou falha. Uma nova tentativa
# repete "em processamento". Concluída e falha são finais: o reprocessamento
# apaga o registro e cria outro.
_TRANSITIONS: dict[TranscriptionStatus, frozenset[TranscriptionStatus]] = {
    TranscriptionStatus.PENDING: frozenset({TranscriptionStatus.PROCESSING, TranscriptionStatus.FAILED}),
    TranscriptionStatus.PROCESSING: frozenset(
        {TranscriptionStatus.PROCESSING, TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED}
    ),
    TranscriptionStatus.COMPLETED: frozenset(),
    TranscriptionStatus.FAILED: frozenset(),
}


class Transcription(BaseEntity):
    """Transcription aggregate root."""

    media_id: UUID
    user_id: Optional[UUID]
    filename: Optional[str]
    correlation_id: Optional[str]
    language: str
    text: str
    segments: list[Dict[str, Any]]
    confidence_score: Optional[float]
    provider: str
    status: TranscriptionStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    error_message: Optional[str]
    speaker_aliases: Dict[str, str]
    processed_at: Optional[datetime.datetime]
    # Duração da gravação, lida ao iniciar: define o prazo do processamento.
    media_duration_seconds: Optional[float]
    # Descrições de quadros do vídeo ("[mm:ss] texto"), feitas após a transcrição.
    visual_context: List[str]

    def __init__(
        self,
        media_id: UUID,
        user_id: Optional[UUID] = None,
        filename: Optional[str] = None,
        correlation_id: Optional[str] = None,
        language: str = "auto",
        text: str = "",
        segments: Optional[list[Dict[str, Any]]] = None,
        confidence_score: Optional[float] = None,
        provider: str = "default",
        status: TranscriptionStatus = TranscriptionStatus.PENDING,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        error_message: Optional[str] = None,
        speaker_aliases: Optional[Dict[str, str]] = None,
        processed_at: Optional[datetime.datetime] = None,
        id: Optional[UUID] = None,
        media_duration_seconds: Optional[float] = None,
        visual_context: Optional[List[str]] = None,
    ):
        super().__init__(id or uuid4())
        self.media_id = media_id
        self.user_id = user_id
        self.filename = filename
        self.correlation_id = correlation_id
        self.language = language
        self.text = text or ""
        self.segments = segments or []
        self.confidence_score = confidence_score
        self.provider = provider
        self.status = status
        self.created_at = created_at or utcnow()
        self.updated_at = updated_at or utcnow()
        self.error_message = error_message
        self.speaker_aliases = speaker_aliases or {}
        self.processed_at: Optional[datetime.datetime] = processed_at
        self.media_duration_seconds = media_duration_seconds
        self.visual_context = list(visual_context or [])

    @property
    def is_finished(self) -> bool:
        """Concluída ou com falha: uma tarefa repetida não tem o que fazer."""
        return self.status in (TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED)

    def _change_to(self, status: TranscriptionStatus, error_message: Optional[str] = None) -> None:
        if status not in _TRANSITIONS[self.status]:
            raise InvalidTranscriptionTransitionError(
                f"A transcrição não pode passar de {self.status.value} para {status.value}."
            )
        self.status = status
        self.error_message = error_message
        self.updated_at = utcnow()

    def mark_as_completed(self, result: Dict[str, Any]) -> None:
        # Sem erro de uma tentativa anterior: a transcrição deu certo.
        self._change_to(TranscriptionStatus.COMPLETED)
        self.text = result.get("text", "")
        self.segments = result.get("segments", [])
        self.language = result.get("language", self.language)
        self.confidence_score = result.get("confidence_score")
        if self.confidence_score is None:
            # Sem segmentos com confiança (texto, OCR): fica vazio, não 0.
            self.confidence_score = transcript_confidence(self.segments)
        self.processed_at = self.updated_at

    def mark_as_extracted(self, text: str, provider: str) -> None:
        """Texto extraído de um documento ou imagem (sem horários)."""
        self.mark_as_completed({"text": text, "segments": []})
        self.provider = provider

    def record_media_duration(self, seconds: float) -> None:
        if seconds and seconds > 0:
            self.media_duration_seconds = float(seconds)

    def attach_visual_context(self, descriptions: List[str]) -> None:
        self.visual_context = [d for d in descriptions if d]

    @property
    def recording_seconds(self) -> Optional[float]:
        """Duração da gravação: a lida do arquivo ou, na falta, o fim do último trecho."""
        if self.media_duration_seconds:
            return self.media_duration_seconds
        if self.segments and isinstance(self.segments[-1], dict):
            return self.segments[-1].get("end") or None
        return None

    def mark_as_processing(self) -> None:
        """Começo de uma tentativa (renova updated_at, base do prazo)."""
        self._change_to(TranscriptionStatus.PROCESSING)

    def record_processing_error(self, error_message: str) -> None:
        """Tentativa que falhou, com outra a caminho."""
        self._change_to(TranscriptionStatus.PROCESSING, error_message)

    def mark_as_failed(self, error_message: str) -> None:
        self._change_to(TranscriptionStatus.FAILED, error_message or "Erro desconhecido")
        self.processed_at = self.updated_at

    def set_speaker_aliases(self, aliases: Dict[str, str]) -> None:
        self.speaker_aliases = aliases
        self.updated_at = utcnow()

    def correct_segment(self, index: int, text: str) -> None:
        """Correção humana de um trecho. O texto do modelo fica em
        ``original_text`` (só na primeira correção), e o texto completo é
        refeito a partir dos trechos: uma nova análise já usa a correção."""
        if self.status != TranscriptionStatus.COMPLETED:
            raise ConflictError("Só uma transcrição concluída pode ser corrigida.")
        if not 0 <= index < len(self.segments):
            raise ValidationError("trecho", str(index), "não existe na transcrição")
        cleaned = " ".join((text or "").split())
        if not cleaned:
            raise ValidationError("texto", text, "o trecho corrigido não pode ficar vazio")
        segment = dict(self.segments[index])
        segment.setdefault("original_text", segment.get("text", ""))
        segment["text"] = cleaned
        self.segments = [*self.segments[:index], segment, *self.segments[index + 1:]]
        self.text = " ".join(str(s.get("text", "")).strip() for s in self.segments if isinstance(s, dict))
        self.updated_at = utcnow()

    @property
    def corrected_segments(self) -> int:
        return sum(1 for s in self.segments if isinstance(s, dict) and "original_text" in s)
