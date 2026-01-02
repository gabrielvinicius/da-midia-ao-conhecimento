"""Adapter de geração de texto usando Transformers (via Hugging Face) para sumarização."""

from __future__ import annotations

import logging
import os
from typing import Optional

from transformers import pipeline

from src.text_analysis.application.ports.text_generation import TextGenerationPort
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = get_logger(__name__)


class TransformersTextGenerationAdapter(TextGenerationPort):
    def __init__(self, model_name: str = "facebook/bart-large-cnn", device: int | str | None = None) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self._available = True
        self._pipe = None
        self._initialized = False
        metrics = SharedPrometheusMetrics()
        self._m_attempts = metrics.get_textgen_transformers_attempts()
        self._m_failures = metrics.get_textgen_transformers_failures()
        self._m_success = metrics.get_textgen_transformers_success()

    def is_available(self) -> bool:
        return self._available

    async def summarize_topic(
        self,
        title_hint: Optional[str],
        content: str,
        keywords: list[str],
        language: str,
    ) -> str:
        self._m_attempts.labels(model=self.model_name).inc()
        if not self._available:
            return self._fallback(title_hint, keywords)

        if not self._initialized:
            try:  # Lazy load
                # Map 'cpu' or device ID
                device_idx = -1 if self.device == "cpu" else 0

                self._pipe = pipeline(
                    task="summarization",
                    model=self.model_name,
                    device=device_idx,
                    token=os.getenv("HF_TOKEN"),
                )
            except Exception as exc:  # pragma: no cover - runtime path
                logger.warning("transformers_generation.load_failed", error=str(exc))
                self._available = False
                return self._fallback(title_hint, keywords)
            self._initialized = True

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
            logger.warning("transformers_generation.failed", error=str(exc))
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
