"""Adapter de geração de texto usando Transformers (via Hugging Face) para sumarização."""

from __future__ import annotations

from typing import Optional


from src.text_analysis.application.ports.text_generation import (
    TextGenerationPort,
    TextGenerationUnavailableError,
)
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    SharedPrometheusMetrics,
)

logger = get_logger(__name__)


class TransformersTextGenerationAdapter(TextGenerationPort):
    def __init__(self, model_name: str = "Qwen/Qwen2.5-3B-Instruct", device: int | str | None = None) -> None:
        self.model_name = model_name
        self.device = device or settings.resolved_device
        self._available = True
        self._pipe = None
        self._initialized = False
        self._is_instruct = any(x in model_name.lower() for x in ["instruct", "chat", "llama", "mistral", "zephyr", "qwen"])
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
        *,
        max_tokens: Optional[int] = None,
    ) -> str:
        self._m_attempts.labels(model=self.model_name).inc()
        if not self._available:
            raise TextGenerationUnavailableError(f"{self.model_name} indisponível")
        self._ensure_loaded()

        try:
            if self._is_instruct:
                summary = self._generate_chat(title_hint, content, keywords, max_tokens)
            else:
                summary = self._generate_summary(title_hint, content, keywords)
        except Exception as exc:  # pragma: no cover - runtime path
            logger.warning("transformers_generation.failed", error=str(exc))
            self._available = False
            self._m_failures.labels(model=self.model_name).inc()
            raise TextGenerationUnavailableError(f"{self.model_name} indisponível")

        self._m_success.labels(model=self.model_name).inc()
        # Garante que o resumo comece pelo título do tópico.
        if not summary.strip().startswith("#"):
            return f"# {title_hint or 'Tópico'}\n{summary}"
        return summary

    def _ensure_loaded(self) -> None:
        """Carrega o pipeline na primeira chamada."""
        if self._initialized:
            return
        try:
            self._pipe = self._load_pipeline()
        except Exception as exc:  # pragma: no cover - runtime path
            logger.warning("transformers_generation.load_failed", error=str(exc))
            self._available = False
            raise TextGenerationUnavailableError(f"{self.model_name} indisponível")
        self._initialized = True

    def _load_pipeline(self):  # pragma: no cover - runtime path
        import torch
        from transformers import BitsAndBytesConfig, pipeline

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        task = "text-generation" if self._is_instruct else "summarization"
        # Modelos grandes só cabem na GPU de 12 GB quantizados em 4 bits.
        is_large_model = any(s in self.model_name for s in ["7B", "8B", "9B", "14B", "30B", "32B"])
        model_kwargs: dict = {
            "max_memory": {0: "10GB"},  # 2 GB ficam para o sistema
            "attn_implementation": "flash_attention_2" if torch.cuda.is_available() else "eager",
        }
        pipeline_kwargs: dict = {
            "task": task,
            "model": self.model_name,
            "device_map": "auto",
            "token": settings.hf_token,
            "model_kwargs": model_kwargs,
        }
        if is_large_model:
            logger.info("transformers_generation.enabling_4bit_quantization", model=self.model_name)
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
        else:
            pipeline_kwargs["torch_dtype"] = torch.float16
        return pipeline(**pipeline_kwargs)

    @staticmethod
    def _chat_messages(title_hint: Optional[str], content: str, keywords: list[str]) -> list[dict]:
        """Separa o prompt de sistema embutido (<<<SYSTEM>>>...<<<END_SYSTEM>>>)
        e, se o conteúdo for só o texto, acrescenta a instrução de resumo."""
        system_prompt = "Você é um assistente especialista em sumarização de textos técnicos."
        user_content = content
        if "<<<SYSTEM>>>" in content and "<<<END_SYSTEM>>>" in content:
            sys_part, user_content = content.split("<<<END_SYSTEM>>>", 1)
            sys_part = sys_part.replace("<<<SYSTEM>>>", "").strip()
            system_prompt = sys_part or system_prompt
            user_content = user_content.strip()

        if "Analise o texto" not in user_content and "[TEXTO]" not in user_content:
            user_content = (
                f"Gere um resumo detalhado e estruturado em Markdown sobre o tópico '{title_hint}'. "
                f"Considere as palavras-chave: {', '.join(keywords)}. \n\n"
                f"Texto base:\n{user_content}"
            )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _generate_chat(
        self, title_hint: Optional[str], content: str, keywords: list[str], max_tokens: Optional[int] = None
    ) -> str:  # pragma: no cover - runtime path
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        outputs = self._pipe(
            self._chat_messages(title_hint, content, keywords),
            max_new_tokens=max_tokens or 3000,
            do_sample=True,
            temperature=0.35,
            top_p=0.82,
            top_k=50,
            repetition_penalty=1.12,
            pad_token_id=151643,
            return_full_text=False,
        )
        return outputs[0]["generated_text"].strip()

    def _generate_summary(self, title_hint: Optional[str], content: str, keywords: list[str]) -> str:  # pragma: no cover - runtime path
        """Modelos de sumarização (BART, T5): título e palavras-chave dão o contexto."""
        prompt = (
            f"Título: {title_hint or 'Tópico'}\n"
            f"Palavras-chave: {', '.join(keywords) if keywords else 'Nenhuma'}\n\n"
            f"Conteúdo:\n{content}"
        )
        return self._pipe(prompt, max_length=220, min_length=60, do_sample=False)[0]["summary_text"]


__all__ = ["TransformersTextGenerationAdapter"]
