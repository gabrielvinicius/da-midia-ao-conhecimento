"""Adapter de geração de texto usando Transformers (via Hugging Face) para sumarização."""

from __future__ import annotations

import logging
from typing import Optional

from transformers import pipeline

from src.text_analysis.application.ports.text_generation import TextGenerationPort
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = logging.getLogger(__name__)


class TransformersTextGenerationAdapter(TextGenerationPort):
    def __init__(self, model_name: str = "facebook/bart-large-cnn", device: int | str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self._available = True
        self._pipe = None
        metrics = SharedPrometheusMetrics()
        self._m_attempts = metrics.get_textgen_transformers_attempts()
        self._m_failures = metrics.get_textgen_transformers_failures()
        self._m_success = metrics.get_textgen_transformers_success()

    def is_available(self) -> bool:
        return self._available

    def summarize_topic(
        self,
        title_hint: Optional[str],
        content: str,
        keywords: list[str],
        language: str,
    ) -> str:
        self._m_attempts.labels(model=self.model_name).inc()
        if not self._available:
            return self._fallback(title_hint, keywords)

        if self._pipe is None:
            try:  # Lazy load
                self._pipe = pipeline(
                    task="summarization",
                    model=self.model_name,
                    device=self.device,
                )
            except Exception as exc:  # pragma: no cover - runtime path
                logger.warning("transformers_generation.load_failed", extra={"error": str(exc)})
                self._available = False
                return self._fallback(title_hint, keywords)

        # Concatena keywords para dar contexto
        prompt = (
            f"Título: {title_hint or 'Tópico'}\n"
            f"Palavras-chave: {', '.join(keywords) if keywords else 'Nenhuma'}\n\n"
            f"Conteúdo:\n{content}"
        )
        try:
            summary = self._pipe(
                prompt,
                max_length=220,
                min_length=60,
                do_sample=False,
            )[0]["summary_text"]
            self._m_success.labels(model=self.model_name).inc()
            return f"# {title_hint or 'Tópico'}\n{summary}"
        except Exception as exc:  # pragma: no cover - runtime path
            logger.warning("transformers_generation.failed", extra={"error": str(exc)})
            self._available = False
            self._m_failures.labels(model=self.model_name).inc()
            return self._fallback(title_hint, keywords)

    def _fallback(self, title_hint: Optional[str], keywords: list[str]) -> str:
        lines = "\n".join(f"- {kw}" for kw in (keywords or ["Não informado"]))
        return (
            f"# {title_hint or 'Tópico'}\n"
            "**Resumo**\n- Não informado\n"
            "**Termos-chave**\n" + lines
        )


__all__ = ["TransformersTextGenerationAdapter"]
