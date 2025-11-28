"""Embedding service port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class EmbeddingServicePort(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[list[float]]:
        """Return vector embeddings for each text string."""

