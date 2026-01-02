"""Transformers-based sentiment adapter with graceful fallback."""

from __future__ import annotations

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.sentiment import SentimentServicePort
from src.text_analysis.domain import Sentiment, SentimentLabel, TextChunk

logger = get_logger(__name__)


class TransformersSentimentAdapter(SentimentServicePort):
    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self._pipeline = None
        self._initialized = False

    def _get_pipeline(self):
        if not self._initialized:
            try:
                from transformers import pipeline

                # Map 'cpu' or device ID
                device_idx = -1 if self.device == "cpu" else 0
                
                self._pipeline = pipeline(
                    "sentiment-analysis", 
                    model=self.model_name, 
                    top_k=None,
                    device=device_idx
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Sentiment model unavailable", error=str(exc)
                )
            self._initialized = True
        return self._pipeline

    def analyze(self, chunks: list[TextChunk], language: str) -> list[Sentiment]:
        pipe = self._get_pipeline()
        if not pipe:
            return self._rule_based(chunks)

        texts = [chunk.text for chunk in chunks]
        try:
            results = pipe(texts, truncation=True)
        except Exception as exc:  # pragma: no cover - runtime failure
            logger.error("Transformer pipeline failed", error=str(exc))
            return self._rule_based(chunks)

        sentiments: list[Sentiment] = []
        for chunk, result in zip(chunks, results):
            if isinstance(result, list):
                result = result[0]
            label = SentimentLabel.normalize(result.get("label", "neu"))
            score = float(result.get("score", 0.5))
            sentiments.append(
                Sentiment(
                    chunk_id=chunk.id, label=label, score=score, text=chunk.text
                )
            )
        return sentiments

    def _rule_based(self, chunks: list[TextChunk]) -> list[Sentiment]:
        sentiments: list[Sentiment] = []
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
            sentiments.append(
                Sentiment(
                    chunk_id=chunk.id, label=label, score=score, text=chunk.text
                )
            )
        return sentiments
