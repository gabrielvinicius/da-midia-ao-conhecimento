"""SentenceTransformer embedding adapter with fallback."""

from __future__ import annotations

import logging
import math
from typing import List

from src.text_analysis.application.ports.embeddings import EmbeddingServicePort

logger = logging.getLogger(__name__)


class SentenceTransformerEmbeddingAdapter(EmbeddingServicePort):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        try:  # pragma: no cover - optional dependency
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception as exc:
            logger.warning("Embedding model unavailable (%s). Using hash fallback.", exc)

    def embed(self, texts: List[str]) -> List[list[float]]:
        if self._model:
            try:
                return [list(vec) for vec in self._model.encode(texts)]
            except Exception as exc:  # pragma: no cover
                logger.error("Embedding encode failed: %s", exc)
        return [self._hash_vector(text) for text in texts]

    def _hash_vector(self, text: str, dim: int = 10) -> list[float]:
        values = [0.0] * dim
        for idx, ch in enumerate(text):
            values[idx % dim] += (ord(ch) % 31) / 100.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

