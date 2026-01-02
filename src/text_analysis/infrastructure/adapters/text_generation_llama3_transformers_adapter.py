"""Adapter de geração de texto usando Meta Llama 3 via Transformers."""

from __future__ import annotations

import logging
import os
from typing import Optional

from transformers import pipeline

from src.text_analysis.application.ports.text_generation import TextGenerationPort
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = get_logger(__name__)


from src.shared.infrastructure.config.settings import settings

class Llama3TransformersTextGenerationAdapter(TextGenerationPort):
    """Utiliza o modelo Instruct do Llama 3 (8B) para sumarização."""

    def __init__(
        self,
        model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        device: str | None = None,
        max_new_tokens: int = 320,
        temperature: float = 0.2,
    ) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._available = True
        self._pipe = None
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

        if self._pipe is None:
            try:  # Lazy load
                token = os.getenv("HF_TOKEN")
                if token:
                    logger.info("llama3.initializing_with_token", token_prefix=token[:4] + "...")
                else:
                    logger.warning("llama3.initializing_without_token")

                # Map 'cpu' or device ID
                device_idx = -1 if self.device == "cpu" else 0

                self._pipe = pipeline(
                    task="text-generation",
                    model=self.model_name,
                    device=device_idx,
                    return_full_text=False,
                    token=token,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("llama3.load_failed", error=str(exc))
                self._available = False
                return self._fallback(title_hint, keywords)

        prompt = (
            f"Resuma em {language} de forma estruturada e concisa.\n"
            f"Título: {title_hint or 'Tópico'}\n"
            f"Palavras-chave: {', '.join(keywords) if keywords else 'Nenhuma'}\n"
            f"Conteúdo:\n{content}\n\n"
            "Formato esperado:\n"
            "# <Título>\n"
            "## Resumo\n- bullet 1\n- bullet 2\n"
            "## Pontos principais\n- ponto 1\n- ponto 2\n"
            "## Riscos/Oportunidades\n- item\n"
        )
        try:
            out = self._pipe(
                prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
            )
            text = out[0]["generated_text"].strip()
            self._m_success.labels(model=self.model_name).inc()
            return text
        except Exception as exc:  # pragma: no cover
            logger.warning("llama3.generation_failed", error=str(exc))
            self._available = False
            self._m_failures.labels(model=self.model_name).inc()
            return self._fallback(title_hint, keywords)

    def _fallback(self, title_hint: Optional[str], keywords: list[str]) -> str:
        lines = "\n".join(f"- {kw}" for kw in (keywords or ["Não informado"]))
        return (
            f"# {title_hint or 'Tópico'}\n"
            "## Resumo\n- Não informado\n"
            "## Pontos principais\n- Não informado\n"
            "## Riscos/Oportunidades\n- Não informado\n"
            "## Palavras-chave\n" + lines
        )


__all__ = ["Llama3TransformersTextGenerationAdapter"]
