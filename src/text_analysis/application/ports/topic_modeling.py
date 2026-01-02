"""Topic modeling port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain import TextChunk, Topic


class TopicModelingPort(ABC):
    @abstractmethod
    def model_topics(
        self, chunks: List[TextChunk], embeddings: List[list[float]], language: str
    ) -> Tuple[List[Topic], dict]:
        """Return topics and diagnostics derived from chunks and embeddings."""

