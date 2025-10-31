# src/summarization/infrastructure/summarizer.py
"""Small, dependency free text summariser used by the service layer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


Sentence = str


def _split_sentences(text: str) -> list[Sentence]:
    sentences: list[Sentence] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+", text):
        end = match.end()
        candidate = text[start:match.start() + 1].strip()
        if candidate:
            sentences.append(candidate)
        start = end
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _normalise_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


@dataclass(slots=True)
class SummarizerOptions:
    max_sentences: int = 3
    min_sentence_length: int = 20

    @classmethod
    def from_mapping(cls, data: Optional[Dict[str, object]]) -> "SummarizerOptions":
        if not data:
            return cls()
        max_sentences = int(data.get("max_sentences", cls.max_sentences))
        min_sentence_length = int(data.get("min_sentence_length", cls.min_sentence_length))
        return cls(max_sentences=max(1, max_sentences), min_sentence_length=max(1, min_sentence_length))


class TextRankSummarizer:
    """A pragmatic summariser that favours the most informative sentences."""

    async def summarize(
        self,
        text_content: str,
        options: Optional[Dict[str, object]] = None,
    ) -> str:
        cleaned = _normalise_whitespace(text_content)
        if not cleaned:
            return ""

        opts = SummarizerOptions.from_mapping(options)
        sentences = _split_sentences(cleaned)

        if not sentences:
            return cleaned

        meaningful: Iterable[Sentence] = (
            sentence for sentence in sentences if len(sentence) >= opts.min_sentence_length
        )

        selected = []
        for sentence in meaningful:
            selected.append(sentence)
            if len(selected) >= opts.max_sentences:
                break

        if not selected:
            selected = sentences[: opts.max_sentences]

        return " ".join(selected)
