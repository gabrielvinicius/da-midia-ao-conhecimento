"""Adapter de geração de texto via Ollama com retries, health e métricas."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from src.text_analysis.application.ports.text_generation import TextGenerationPort
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    timeout: int = 20


PROMPT_TEMPLATE = """\
# {title}
## Resumo
- {summary_bullet_1}
- {summary_bullet_2}
## Subtópicos
1. **{sub1}**
   - {sub1_detail}
2. **{sub2}**
   - {sub2_detail}
## Termos-chave
{keywords_block}

Instruções:
- Responda em {language}.
- Não invente fatos; se faltar informação, escreva "Não informado".
- Seja conciso (máx. ~200 palavras).

Conteúdo de origem:
{content}
"""


class OllamaTextGenerationAdapter(TextGenerationPort):
    """Geração via Ollama; mantém fallback determinístico para disponibilidade."""

    def __init__(
        self,
        model: str = "llama3.1:8b",
        host: str = "http://localhost:11434",
        timeout: int = 20,
        retries: int = 2,
        retry_cooldown: int = 60,
    ) -> None:
        self.config = OllamaConfig(host=host, model=model, timeout=timeout)
        self._available = True
        self._retries = retries
        self._retry_cooldown = retry_cooldown
        self._last_failure_ts: float | None = None
        metrics = SharedPrometheusMetrics()
        self._m_attempts = metrics.get_textgen_ollama_attempts()
        self._m_failures = metrics.get_textgen_ollama_failures()
        self._m_retries = metrics.get_textgen_ollama_retries()

    def is_available(self) -> bool:
        return self._available

    async def summarize_topic(
        self,
        title_hint: Optional[str],
        content: str,
        keywords: list[str],
        language: str,
    ) -> str:
        self._m_attempts.labels(model=self.config.model).inc()
        # tenta reativar se estava indisponível e cooldown já passou
        if not self._available and self._last_failure_ts:
            if time.time() - self._last_failure_ts > self._retry_cooldown:
                if await self.health_check():
                    self._available = True
                    self._last_failure_ts = None

        prompt = PROMPT_TEMPLATE.format(
            title=title_hint or "Tópico",
            content=content or "Não informado",
            keywords_block="\n".join(f"- {kw}" for kw in (keywords or ["Não informado"])),
            language=language,
            summary_bullet_1="Não informado",
            summary_bullet_2="",
            sub1="Aspecto principal",
            sub1_detail="Não informado",
            sub2="Risco/Oportunidade",
            sub2_detail="Não informado",
        )
        try:
            last_exc = None
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                for attempt in range(self._retries + 1):
                    try:
                        resp = await client.post(
                            f"{self.config.host}/api/generate",
                            json={"model": self.config.model, "prompt": prompt, "stream": False},
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        return data.get("response", "Não informado")
                    except Exception as exc:  # pragma: no cover
                        last_exc = exc
                        self._m_retries.labels(model=self.config.model).inc()
                        logger.warning(
                            "ollama.generation_retry",
                            error=str(exc),
                            attempt=attempt + 1,
                        )
                if last_exc:
                    raise last_exc
        except Exception as exc:  # pragma: no cover - chamada externa
            logger.warning("ollama.generation_failed", error=str(exc))
            self._available = False
            self._last_failure_ts = time.time()
            self._m_failures.labels(model=self.config.model).inc()
            return self._fallback(title_hint, keywords)

    def _fallback(self, title_hint: Optional[str], keywords: list[str]) -> str:
        lines = "\n".join(f"- {kw}" for kw in (keywords or ["Não informado"]))
        return (
            f"# {title_hint or 'Tópico'}\n"
            "## Resumo\n- Não informado\n"
            "## Subtópicos\n1. **Não informado**\n   - Não informado\n"
            "## Termos-chave\n" + lines
        )

    async def health_check(self) -> bool:
        """Ping leve para validar disponibilidade sem gerar conteúdo."""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                resp = await client.get(f"{self.config.host}/api/tags")
                resp.raise_for_status()
                return True
        except Exception:
            return False
