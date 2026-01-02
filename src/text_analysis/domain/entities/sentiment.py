from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

    @classmethod
    def normalize(cls, label: str) -> "SentimentLabel":
        try:
            return cls(label.lower())
        except Exception:
            return cls.NEUTRAL


@dataclass
class TextChunk:
    id: str
    text: str
    start: float | None = None
    end: float | None = None

    @classmethod
    def from_text(cls, text: str) -> "TextChunk":
        return cls(id=str(uuid4()), text=text)


@dataclass
class Sentiment:
    chunk_id: str
    label: SentimentLabel
    score: float
    text: str = ""
