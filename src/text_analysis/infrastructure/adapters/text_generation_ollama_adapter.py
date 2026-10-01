"""Adapter de geração de texto via Ollama com retries, modelo reserva e métricas."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)
from src.text_analysis.application.ports.text_generation import (
    TextGenerationPort,
    TextGenerationUnavailableError,
)

logger = get_logger(__name__)

SYSTEM_START = "<<<SYSTEM>>>"
SYSTEM_END = "<<<END_SYSTEM>>>"
DEFAULT_SYSTEM_PROMPT = "Você é um assistente que resume conteúdos com fidelidade, sem inventar fatos."


@dataclass(slots=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "qwen3.5:9b"
    fallback_model: Optional[str] = None
    timeout: int = 900
    # Janela fixa (mudar num_ctx entre chamadas obriga o Ollama a recarregar o
    # modelo). 16k tokens bastam para os prompts do pipeline: a síntese envia
    # a transcrição inteira só até ~36 mil caracteres e, acima disso, blocos.
    # Com 32k, o cache de contexto ocupava vários GB a mais da GPU de 12 GB.
    context_tokens: int = 16384
    temperature: float = 0.2
    keep_alive: str = "5m"


def split_system_prompt(content: str) -> tuple[str, str]:
    """Separa o bloco <<<SYSTEM>>>...<<<END_SYSTEM>>> do restante do prompt."""
    if SYSTEM_START in content and SYSTEM_END in content:
        head, _, rest = content.partition(SYSTEM_END)
        system = head.split(SYSTEM_START, 1)[1].strip()
        return (system or DEFAULT_SYSTEM_PROMPT), rest.strip()
    return DEFAULT_SYSTEM_PROMPT, content


class OllamaTextGenerationAdapter(TextGenerationPort):
    """Geração via API de chat do Ollama.

    - O modo de raciocínio ("thinking") dos modelos Qwen3/Qwen3.5 é desligado,
      pois só aumentaria o tempo de resposta de um resumo.
    - Se o modelo principal falhar, tenta o modelo reserva e marca
      ``last_used_reserve``.
    - Se ambos falharem, lança ``TextGenerationUnavailableError``: quem chama
      decide o substituto (ver a porta).
    """

    provider_name = "ollama"

    def __init__(
        self,
        model: str = "qwen3.5:9b",
        host: str = "http://localhost:11434",
        timeout: int = 900,
        retries: int = 1,
        retry_cooldown: int = 60,
        fallback_model: Optional[str] = None,
        context_tokens: int = 16384,
    ) -> None:
        self.config = OllamaConfig(
            host=host.rstrip("/"),
            model=model,
            fallback_model=fallback_model if fallback_model and fallback_model != model else None,
            timeout=timeout,
            context_tokens=context_tokens,
        )
        self.model_name = model
        self._available = True
        self._retries = retries
        self._retry_cooldown = retry_cooldown
        self._last_failure_ts: float | None = None
        self.last_used_reserve = False
        self.last_model_used: Optional[str] = None
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
        self.last_used_reserve = False
        self._m_attempts.labels(model=self.config.model).inc()
        # tenta reativar se estava indisponível e o cooldown já passou
        if not self._available and self._last_failure_ts:
            if time.time() - self._last_failure_ts > self._retry_cooldown:
                if await self.health_check():
                    self._available = True
                    self._last_failure_ts = None

        system, user = split_system_prompt(content or "")
        if SYSTEM_START not in (content or ""):
            user = self._wrap_raw_content(title_hint, user, keywords, language)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        models = [self.config.model] + ([self.config.fallback_model] if self.config.fallback_model else [])
        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for model in models:
                for attempt in range(self._retries + 1):
                    try:
                        text = await self._chat(client, model, messages)
                        self._available = True
                        self.last_model_used = model
                        self.last_used_reserve = model != self.config.model
                        return text
                    except Exception as exc:  # chamada externa
                        last_exc = exc
                        self._m_retries.labels(model=model).inc()
                        logger.warning(
                            "ollama.generation_retry",
                            model=model,
                            error=str(exc),
                            attempt=attempt + 1,
                        )

        logger.warning("ollama.generation_failed", error=str(last_exc))
        self._available = False
        self._last_failure_ts = time.time()
        self._m_failures.labels(model=self.config.model).inc()
        raise TextGenerationUnavailableError(
            f"Nenhum modelo de linguagem respondeu ({', '.join(models)}): {last_exc}"
        )

    async def _chat(self, client: httpx.AsyncClient, model: str, messages: list[dict]) -> str:
        resp = await client.post(
            f"{self.config.host}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "think": False,
                "keep_alive": self.config.keep_alive,
                "options": {
                    "num_ctx": self.config.context_tokens,
                    "temperature": self.config.temperature,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("message") or {}).get("content") or data.get("response") or ""
        text = text.strip()
        if not text:
            raise ValueError("resposta vazia do Ollama")
        return text

    @staticmethod
    def _wrap_raw_content(
        title_hint: Optional[str], content: str, keywords: list[str], language: str
    ) -> str:
        """Instrução padrão quando o chamador envia apenas o texto de origem."""
        kw = ", ".join(keywords) if keywords else "não informadas"
        return (
            f"Resuma o conteúdo abaixo sobre '{title_hint or 'o tema'}' em {language}, "
            "em Markdown, sem inventar informações.\n"
            f"Palavras-chave: {kw}\n\n"
            f"{content or 'Não informado'}"
        )

    async def release(self) -> None:
        """Descarrega os modelos da GPU (keep_alive=0); a próxima chamada os recarrega."""
        models = [self.config.model] + ([self.config.fallback_model] if self.config.fallback_model else [])
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for model in models:
                    await client.post(
                        f"{self.config.host}/api/generate",
                        json={"model": model, "keep_alive": 0},
                    )
        except Exception as exc:  # liberar memória nunca derruba a análise
            logger.warning("ollama.release_failed", error=str(exc))

    async def health_check(self) -> bool:
        """Ping leve para validar disponibilidade sem gerar conteúdo."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.config.host}/api/tags")
                resp.raise_for_status()
                return True
        except Exception:
            return False
