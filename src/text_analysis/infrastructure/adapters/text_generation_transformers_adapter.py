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
    ) -> str:
        self._m_attempts.labels(model=self.model_name).inc()
        if not self._available:
            return self._fallback(title_hint, keywords)

        if not self._initialized:
            try:  # Lazy load
                # Map 'cpu' or device ID
                device_idx = -1 if self.device == "cpu" else 0
                
                # Determine task based on model type
                task = "text-generation" if self._is_instruct else "summarization"

                import torch
                torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16

                self._pipe = pipeline(
                    task=task,
                    model=self.model_name,
                    device=device_idx,
                    torch_dtype=torch_dtype, # Correct way to pass it to pipeline
                    token=settings.hf_token,
                )
            except Exception as exc:  # pragma: no cover - runtime path
                logger.warning("transformers_generation.load_failed", error=str(exc))
                self._available = False
                return self._fallback(title_hint, keywords)
            self._initialized = True

        try:
            if self._is_instruct:
                # Handle Instruct Models (Qwen, Mistral, Llama)
                has_instruction = "Analise o texto" in content or "[TEXTO]" in content
                
                # Construct messages for Chat Templates if supported by pipeline
                # otherwise fallback to string prompting
                
                if has_instruction:
                    # Content already contains instruction
                    user_content = content
                else:
                    user_content = (
                        f"Gere um resumo detalhado e estruturado em Markdown sobre o tópico '{title_hint}'. "
                        f"Considere as palavras-chave: {', '.join(keywords)}. \n\n"
                        f"Texto base:\n{content}"
                    )
                
                # Try to use chat template via messages list
                messages = [
                    {"role": "system", "content": "Você é um assistente especialista em sumarização de textos técnicos."},
                    {"role": "user", "content": user_content}
                ]
                
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                # Pipeline 'text-generation' handles list of dicts by applying chat_template automatically
                outputs = self._pipe(
                    messages,
                    max_new_tokens=256, # Reduced from 1024
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    return_full_text=False # Return only generated part
                )
                summary = outputs[0]["generated_text"].strip()
                
            else:
                # Handle Standard Summarization Models (e.g., BART, T5)
                # Concatena keywords para dar contexto
                prompt = (
                    f"Título: {title_hint or 'Tópico'}\n"
                    f"Palavras-chave: {', '.join(keywords) if keywords else 'Nenhuma'}\n\n"
                    f"Conteúdo:\n{content}"
                )
                
                summary = self._pipe(
                    prompt,
                    max_length=220,
                    min_length=60,
                    do_sample=False,
                )[0]["summary_text"]

            self._m_success.labels(model=self.model_name).inc()
            
            # Ensure it starts with the title if not present (simple cleanup)
            if not summary.strip().startswith("#"):
                 return f"# {title_hint or 'Tópico'}\n{summary}"
            return summary

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
