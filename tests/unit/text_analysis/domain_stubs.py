from dataclasses import dataclass


@dataclass
class Document:
    text: str
    segments: list

    @classmethod
    def from_payload(cls, text: str, segments: list | None = None):
        if not text:
            raise ValueError("Empty text")
        return cls(text=text, segments=segments or [])


@dataclass
class Analysis:
    id: str = "analysis-id"


class SentimentLabel:
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

