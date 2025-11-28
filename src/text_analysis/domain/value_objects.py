"""Domain value objects for text analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SentimentLabel(str, Enum):
    POSITIVE = "POS"
    NEUTRAL = "NEU"
    NEGATIVE = "NEG"

    @classmethod
    def normalize(cls, raw: str) -> "SentimentLabel":
        text = (raw or "").strip().lower()
        if text.startswith("pos") or text in {"positive", "positif", "positivo"}:
            return cls.POSITIVE
        if text.startswith("neu") or text in {"neutral", "neutro", "neutre"}:
            return cls.NEUTRAL
        return cls.NEGATIVE


@dataclass(frozen=True, slots=True)
class TextChunk:
    id: str
    text: str
    start: Optional[float] = None
    end: Optional[float] = None


@dataclass(frozen=True, slots=True)
class Sentiment:
    chunk_id: str
    label: SentimentLabel
    score: float


@dataclass(frozen=True, slots=True)
class Topic:
    topic_id: int
    keywords: list[str]
    snippets: list[str]
    title: Optional[str] = None
    summary_md: Optional[str] = None
    size: int = 0
    diagnostics: Optional[dict] = None

