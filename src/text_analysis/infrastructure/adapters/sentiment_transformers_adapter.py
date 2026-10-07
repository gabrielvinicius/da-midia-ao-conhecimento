"""Sentimento por trecho com um modelo do Transformers.

Antes, se o modelo não carregasse, o adaptador classificava os trechos por
palavras-chave ("bom", "ruim") sem avisar. Foi o que aconteceu em todas as
análises: faltava o pacote sentencepiece, que o tokenizador do XLM-RoBERTa
exige, e o "tom" das análises vinha das palavras-chave. Agora, sem o modelo,
o adaptador lança o erro: a etapa (opcional) fica registrada como falha e as
demais seguem sem o tom.
"""

from __future__ import annotations

from src.shared.domain.errors import TemporarilyUnavailableError
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

                self._pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    top_k=None,
                    device=-1 if self.device == "cpu" else 0,
                )
            except Exception as exc:  # pragma: no cover
                logger.error("sentiment.model_unavailable", model=self.model_name, error=str(exc))
            self._initialized = True
        return self._pipeline

    def analyze(self, chunks: list[TextChunk], language: str) -> list[Sentiment]:
        pipe = self._get_pipeline()
        if not pipe:
            raise TemporarilyUnavailableError(f"Modelo de sentimento indisponível ({self.model_name}).")
        results = pipe([chunk.text for chunk in chunks], truncation=True)

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
