"""Adapter de geração de texto via Ollama com retries, modelo reserva e métricas."""

from __future__ import annotations

import re
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
# Fração da janela a partir da qual o prompt é tratado como possivelmente cortado.
TRUNCATION_RATIO = 0.97
DEFAULT_SYSTEM_PROMPT = "Você é um assistente que resume conteúdos com fidelidade, sem inventar fatos."
# Quando a resposta bate no teto (done_reason "length"), pede a continuação
# até este número de vezes. Antes, o resumo era entregue cortado no meio de
# uma frase e sem a conclusão, e nada indicava isso.
MAX_CONTINUATIONS = 2
CONTINUE_PROMPT = (
    "Continue o texto exatamente de onde parou, sem repetir o que já escreveu "
    "e sem comentar a interrupção. Conclua as seções que faltam."
)
_SENTENCE_END = re.compile(r"[.!?…][\"”')\]]*(?=\s|$)")
_ENDS_SENTENCE = re.compile(r"[.!?…][\"”')\]]*$")


def trim_incomplete_ending(text: str) -> str:
    """Corta a frase inacabada do fim (resposta interrompida pelo teto).

    Mantém até o último ponto final, ou até a última linha completa de uma
    lista; títulos que ficariam sem conteúdo também saem.
    """
    text = text.rstrip()
    if not text or _ENDS_SENTENCE.search(text):
        return text
    ends = [m.end() for m in _SENTENCE_END.finditer(text)]
    last_line = text.rfind("\n")
    cut = max(ends[-1] if ends else -1, last_line)
    if cut <= 0:
        return text
    lines = text[:cut].rstrip().splitlines()
    while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("#")):
        lines.pop()
    return "\n".join(lines).rstrip()


def _joined(previous: str, continuation: str) -> str:
    """Emenda a continuação depois de uma frase completa."""
    continuation = continuation.strip()
    starts_block = continuation[:1] in {"#", "-", "*", "|", ">"} or continuation[:2].rstrip(".").isdigit()
    return previous + ("\n\n" if starts_block else " ") + continuation


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
        *,
        max_tokens: Optional[int] = None,
    ) -> str:
        self.last_used_reserve = False
        self.last_prompt_tokens = None
        self.last_prompt_truncated = False
        self.last_response_truncated = False
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
                        text = await self._complete(client, model, messages, max_tokens)
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

    async def _complete(
        self, client: httpx.AsyncClient, model: str, messages: list[dict], max_tokens: Optional[int] = None
    ) -> str:
        """Resposta inteira: se bater no teto, pede a continuação.

        Cada continuação parte da última frase completa, para a emenda não
        cair no meio de uma palavra. Se ainda faltar texto depois de
        ``MAX_CONTINUATIONS`` pedidos, devolve até a última frase completa e
        marca ``last_response_truncated``.
        """
        text, reason = await self._chat(client, model, messages, max_tokens)
        continuations = 0
        while reason == "length" and max_tokens and continuations < MAX_CONTINUATIONS:
            continuations += 1
            text = trim_incomplete_ending(text)
            follow_up = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": CONTINUE_PROMPT},
            ]
            try:
                more, reason = await self._chat(client, model, follow_up, max_tokens)
            except ValueError:  # continuação vazia: o modelo considerou o texto pronto
                reason = "stop"
                break
            text = _joined(text, more)
        if reason == "length":
            self.last_response_truncated = True
            text = trim_incomplete_ending(text)
            logger.warning("ollama.response_truncated", model=model, max_tokens=max_tokens)
        elif continuations:
            logger.info("ollama.response_continued", model=model, continuations=continuations)
        return text

    async def _chat(
        self, client: httpx.AsyncClient, model: str, messages: list[dict], max_tokens: Optional[int] = None
    ) -> tuple[str, Optional[str]]:
        """Texto da resposta e o motivo do fim ("stop" ou "length", o teto)."""
        options: dict = {"num_ctx": self.config.context_tokens, "temperature": self.config.temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        resp = await client.post(
            f"{self.config.host}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "think": False,
                "keep_alive": self.config.keep_alive,
                "options": options,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._check_prompt_size(model, data.get("prompt_eval_count"))
        text = (data.get("message") or {}).get("content") or data.get("response") or ""
        text = text.strip()
        if not text:
            raise ValueError("resposta vazia do Ollama")
        return text, data.get("done_reason")

    def _check_prompt_size(self, model: str, prompt_tokens: Optional[int]) -> None:
        """O Ollama corta, sem erro, o prompt que não cabe na janela (num_ctx).
        Um prompt que ocupa a janela quase inteira provavelmente foi cortado."""
        if not isinstance(prompt_tokens, int):
            return
        self.last_prompt_tokens = prompt_tokens
        if prompt_tokens >= self.config.context_tokens * TRUNCATION_RATIO:
            self.last_prompt_truncated = True
            logger.warning(
                "ollama.prompt_may_be_truncated",
                model=model,
                prompt_tokens=prompt_tokens,
                context_tokens=self.config.context_tokens,
            )

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
