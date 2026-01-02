from __future__ import annotations

import math
from typing import Optional

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.embeddings import EmbeddingServicePort

logger = get_logger(__name__)


class SentenceTransformerEmbeddingAdapter(EmbeddingServicePort):
    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            try:  # pragma: no cover
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as exc:
                logger.warning(
                    "Embedding model unavailable", error=str(exc)
                )
            self._initialized = True
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        if model:
            try:
                return [list(vec) for vec in model.encode(texts)]
            except Exception as exc:  # pragma: no cover
                logger.error("Embedding encode failed", error=str(exc))
        return [self._hash_vector(text) for text in texts]

    def _hash_vector(self, text: str, dim: int = 10) -> list[float]:
        values = [0.0] * dim
        for idx, ch in enumerate(text):
            values[idx % dim] += (ord(ch) % 31) / 100.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
