"""Reranqueador com um cross-encoder (sentence-transformers)."""
from __future__ import annotations

import math

from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.text_analysis.application.ports.reranking import RerankerPort

logger = get_logger(__name__)


class CrossEncoderRerankerAdapter(RerankerPort):
    """Lê pergunta e trecho juntos (ex.: BAAI/bge-reranker-v2-m3, multilíngue).

    O modelo é carregado na primeira busca. Se não carregar, ``score`` lança
    o erro e a busca mantém a ordem dos vetores.
    """

    def __init__(self, model_name: str, device: str | None = None, max_length: int = 512) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self.max_length = max_length
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            logger.info("reranker.loading_model", model=self.model_name, device=self.device)
            self._model = CrossEncoder(self.model_name, device=self.device, max_length=self.max_length)
        return self._model

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        raw = self._get_model().predict([(query, p) for p in passages])
        scores = [float(s) for s in raw]
        # Modelos de um rótulo devolvem a probabilidade (0 a 1); se vierem
        # logits, convertem-se para a mesma escala.
        if any(s < 0 or s > 1 for s in scores):
            scores = [1 / (1 + math.exp(-s)) for s in scores]
        return scores


__all__ = ["CrossEncoderRerankerAdapter"]
