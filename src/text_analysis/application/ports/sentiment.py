"""Sentiment analysis service port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ...domain import Sentiment, TextChunk


class SentimentServicePort(ABC):
    @abstractmethod
    def analyze(self, chunks: List[TextChunk], language: str) -> List[Sentiment]:
        """Return sentiment for each chunk in order."""

