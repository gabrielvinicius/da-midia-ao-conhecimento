"""Eventos de integração: a linguagem publicada entre os módulos.

Ficam no núcleo compartilhado porque são o contrato entre os contextos, mas
cada evento tem um único módulo que o publica (``published_by``). Os demais
apenas reagem a ele. Um teste de arquitetura confere que nenhum outro módulo
cria o evento.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar, List, Optional
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DomainEvent:
    """Envelope comum. Os dados de cada evento são campos tipados da própria
    classe, nunca um dicionário livre: assim quem reage sabe o que recebe."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_now)
    correlation_id: Optional[str] = None

    @property
    def event_name(self) -> str:
        return self.__class__.__name__


# --- Core media events ---
@dataclass
class MediaUploaded(DomainEvent):
    published_by: ClassVar[str] = "media_management"

    media_id: str = ""
    user_id: Optional[str] = None
    filename: Optional[str] = None
    media_type: Optional[str] = None
    storage_provider: Optional[str] = None
    transcription_provider: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    language: Optional[str] = None


@dataclass
class MediaDeleted(DomainEvent):
    published_by: ClassVar[str] = "media_management"

    media_id: str = ""
    reason: Optional[str] = None
    user_id: Optional[str] = None
    triggered_by: Optional[str] = None
    actor_id: Optional[str] = None


@dataclass
class MediaReprocessRequested(DomainEvent):
    published_by: ClassVar[str] = "media_management"

    media_id: str = ""
    triggered_by: Optional[str] = None
    actor_id: Optional[str] = None
    requested_by: Optional[str] = None
    note: Optional[str] = None


@dataclass
class MediaFailed(DomainEvent):
    """A mídia foi dada como falha pelo próprio módulo de mídias (ex.: o
    processamento nunca começou)."""

    published_by: ClassVar[str] = "media_management"

    media_id: str = ""
    user_id: Optional[str] = None
    stage: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class MediaProcessingStarted(DomainEvent):
    published_by: ClassVar[str] = "media_processing"

    media_id: str = ""
    stage: Optional[str] = None


@dataclass
class MediaProcessingCompleted(DomainEvent):
    published_by: ClassVar[str] = "media_processing"

    media_id: str = ""
    stage: Optional[str] = None
    result_id: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class MediaProcessingFailed(DomainEvent):
    published_by: ClassVar[str] = "media_processing"

    media_id: str = ""
    stage: Optional[str] = None
    error_message: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class TranscriptionCompleted(DomainEvent):
    published_by: ClassVar[str] = "media_processing"

    media_id: str = ""
    transcription_id: str = ""
    text: Optional[str] = None
    user_id: Optional[str] = None
    provider: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    filename: Optional[str] = None


@dataclass
class TranscriptionFailed(DomainEvent):
    published_by: ClassVar[str] = "media_processing"

    media_id: str = ""
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class TextContentReady(DomainEvent):
    published_by: ClassVar[str] = "media_management"

    media_id: str = ""
    transcription_id: Optional[str] = None
    text: Optional[str] = None
    user_id: Optional[str] = None
    filename: Optional[str] = None
    language: Optional[str] = None


# --- Text analysis outputs ---
@dataclass
class AnalysisCompleted(DomainEvent):
    """Fim da análise de uma mídia. É o ponto de entrada de novas camadas
    (avisos hoje; catálogo e tendências depois): traz o que a análise achou
    em campos simples, sem obrigar quem reage a ler a análise inteira."""

    published_by: ClassVar[str] = "text_analysis"

    analysis_id: str = ""
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None
    summary_source: Optional[str] = None
    overall_sentiment: Optional[str] = None
    topic_titles: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)


@dataclass
class AnalysisFailed(DomainEvent):
    """A análise falhou de vez (última tentativa ou erro que não passa sozinho)."""

    published_by: ClassVar[str] = "text_analysis"

    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "MediaDeleted",
    "MediaReprocessRequested",
    "MediaFailed",
    "MediaProcessingStarted",
    "MediaProcessingCompleted",
    "MediaProcessingFailed",
    "TranscriptionCompleted",
    "TranscriptionFailed",
    "TextContentReady",
    "AnalysisCompleted",
    "AnalysisFailed",
]
