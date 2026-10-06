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
        """Converte rótulos de diferentes modelos para o rótulo do domínio.

        Aceita "positive"/"neutral"/"negative" (e abreviações), rótulos em
        estrelas ("1 star" a "5 stars") e os genéricos LABEL_0/1/2.
        """
        value = (label or "").strip().lower()
        aliases = {
            "pos": cls.POSITIVE,
            "neg": cls.NEGATIVE,
            "neu": cls.NEUTRAL,
            "label_0": cls.NEGATIVE,
            "label_1": cls.NEUTRAL,
            "label_2": cls.POSITIVE,
        }
        if value in aliases:
            return aliases[value]
        if value[:1].isdigit() and "star" in value:
            stars = int(value[0])
            if stars <= 2:
                return cls.NEGATIVE
            if stars >= 4:
                return cls.POSITIVE
            return cls.NEUTRAL
        try:
            return cls(value)
        except ValueError:
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
