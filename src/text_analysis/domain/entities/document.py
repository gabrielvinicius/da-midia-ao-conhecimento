from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from .sentiment import SentimentLabel


@dataclass
class Document:
    id: UUID
    text: str
    segments: Optional[list] = None

    @classmethod
    def from_payload(cls, text: str, segments: Optional[list] = None) -> "Document":
        return cls(id=uuid4(), text=text or "", segments=segments or [])


@dataclass
class Analysis:
    id: UUID
    document: Document
    media_id: Optional[UUID] = None
    transcription_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    sentiments: list = field(default_factory=list)
    overall_sentiment: Optional[SentimentLabel] = None
    topics: list = field(default_factory=list)
    summary: Optional[str] = None
    diagnostics: dict = field(default_factory=dict)
    chunks: list = field(default_factory=list)
    # Vetores dos trechos (mesma ordem de ``chunks``), calculados uma vez e
    # usados pelos temas, pela indexação e pela verificação de fidelidade.
    # Transitório: não é gravado com a análise.
    chunk_embeddings: list = field(default_factory=list, repr=False)

    @classmethod
    def new(
        cls,
        document: Document,
        *,
        media_id: Optional[UUID] = None,
        transcription_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> "Analysis":
        return cls(
            id=uuid4(),
            document=document,
            media_id=media_id,
            transcription_id=transcription_id,
            user_id=user_id,
        )

