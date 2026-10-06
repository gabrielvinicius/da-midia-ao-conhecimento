"""Embedding service port."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingServicePort(ABC):
    @abstractmethod
    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        """Return vector embeddings for each text string.

        ``kind`` distingue o conteúdo indexado ("passage") das perguntas de
        busca ("query"); modelos como o E5 exigem prefixos diferentes para cada um.
        """
