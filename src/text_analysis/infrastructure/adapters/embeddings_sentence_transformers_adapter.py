from __future__ import annotations

import math

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

    def get_model_instance(self):
        """Expose the internal model instance, initializing if necessary."""
        return self._get_model()

    def embed(self, texts: list[str], kind: str = "passage") -> list[list[float]]:
        model = self._get_model()
        if model:
            try:
                inputs = [self._with_prefix(text, kind) for text in texts]
                vectors = model.encode(inputs, normalize_embeddings=True)
                return [[float(v) for v in vec] for vec in vectors]
            except Exception as exc:  # pragma: no cover
                logger.error("Embedding encode failed", error=str(exc))
        return [self._hash_vector(text) for text in texts]

    def _with_prefix(self, text: str, kind: str) -> str:
        """Modelos E5 foram treinados com os prefixos "query: " e "passage: "."""
        if "e5" not in self.model_name.lower():
            return text
        prefix = "query: " if kind == "query" else "passage: "
        return text if text.startswith(prefix) else prefix + text

    def _hash_vector(self, text: str, dim: int = 384) -> list[float]:
        # Mesmo tamanho da coluna knowledge_chunks.embedding, para não quebrar a gravação.
        values = [0.0] * dim
        for idx, ch in enumerate(text):
            values[idx % dim] += (ord(ch) % 31) / 100.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
