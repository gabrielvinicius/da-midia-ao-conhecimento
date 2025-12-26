"""Adapter de geração de texto usando Meta Llama 3 via Transformers."""

from __future__ import annotations

import logging
from typing import Optional

from transformers import pipeline

from src.text_analysis.application.ports.text_generation import TextGenerationPort
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = logging.getLogger(__name__)


class Llama3TransformersTextGenerationAdapter(TextGenerationPort):
    """Utiliza o modelo Instruct do Llama 3 (8B) para sumarização."""

    def __init__(
        self,
        model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        device: int | str | None = None,
        max_new_tokens: int = 320,
        temperature: float = 0.2,
    ) -> None:
        self.model_name = model_name
        self.device = device
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
                    task="text-generation",
                    model=self.model_name,
                    device=self.device,
                    return_full_text=False,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("llama3.load_failed", extra={"error": str(exc)})
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
            logger.warning("llama3.generation_failed", extra={"error": str(exc)})
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
