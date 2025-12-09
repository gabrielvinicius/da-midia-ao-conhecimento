"""Transformers-based sentiment adapter with graceful fallback."""

from __future__ import annotations

import logging
from typing import List

from src.text_analysis.application.ports.sentiment import SentimentServicePort
from src.text_analysis.domain.value_objects import Sentiment, SentimentLabel, TextChunk

logger = logging.getLogger(__name__)


class TransformersSentimentAdapter(SentimentServicePort):
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._pipeline = None
        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "sentiment-analysis", model=model_name, top_k=None
            )
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("Sentiment model unavailable (%s). Using rule fallback.", exc)

    def analyze(self, chunks: List[TextChunk], language: str) -> List[Sentiment]:
        if not self._pipeline:
            return self._rule_based(chunks)

        texts = [chunk.text for chunk in chunks]
        try:
            results = self._pipeline(texts, truncation=True)
        except Exception as exc:  # pragma: no cover - runtime failure
            logger.error("Transformer pipeline failed: %s", exc)
            return self._rule_based(chunks)

        sentiments: List[Sentiment] = []
        for chunk, result in zip(chunks, results):
            if isinstance(result, list):
                result = result[0]
            label = SentimentLabel.normalize(result.get("label", "neu"))
            score = float(result.get("score", 0.5))
            sentiments.append(Sentiment(chunk_id=chunk.id, label=label, score=score))
        return sentiments

    def _rule_based(self, chunks: List[TextChunk]) -> List[Sentiment]:
        sentiments: List[Sentiment] = []
        for chunk in chunks:
            lowered = chunk.text.lower()
            if any(word in lowered for word in ["bom", "excelente", "good", "ótimo"]):
                label = SentimentLabel.POSITIVE
                score = 0.7
            elif any(
                word in lowered for word in ["ruim", "bad", "pior", "terrível"]
            ):
                label = SentimentLabel.NEGATIVE
                score = 0.7
            else:
                label = SentimentLabel.NEUTRAL
                score = 0.5
            sentiments.append(Sentiment(chunk_id=chunk.id, label=label, score=score))
        return sentiments

