"""Ollama LLM adapter for topic summarization."""

from __future__ import annotations

import logging
from typing import Optional

from ..application.ports import TextGenerationPort

logger = logging.getLogger(__name__)


PROMPT_TEMPLATE = """
Gere um resumo estruturado em Markdown sobre o tópico abaixo.
Use o formato fixo:

# {title}
**Resumo**
- bullet 1
- bullet 2
**Subtópicos**
1. **Subtópico**
   - bullet
2. **Subtópico**
   - bullet
**Termos-chave**
- termo1
- termo2

REGRAS:
- Não invente fatos; se faltar informação, escreva "Não informado".
- Não repita frases.
- Idioma: {language}

Conteúdo:
{content}
Palavras-chave: {keywords}
"""


class OllamaTextGenerationAdapter(TextGenerationPort):
    def __init__(self, model: str = "llama3.1:8b") -> None:
        self.model = model
        self._available = True

    def is_available(self) -> bool:
        return self._available

    def summarize_topic(
        self, title_hint: Optional[str], content: str, keywords: list[str], language: str
    ) -> str:
        prompt = PROMPT_TEMPLATE.format(
            title=title_hint or "Tópico",
            content=content or "Não informado",
            keywords=", ".join(keywords) or "Não informado",
            language=language,
        )
        try:
            import requests

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Não informado")
        except Exception as exc:  # pragma: no cover - external call
            logger.warning("Ollama generation failed, using fallback: %s", exc)
            self._available = False
            return self._fallback(title_hint, keywords)

    def _fallback(self, title_hint: Optional[str], keywords: list[str]) -> str:
        lines = "\n".join(f"- {kw}" for kw in (keywords or ["Não informado"]))
        return (
            f"# {title_hint or 'Tópico'}\n"
            "**Resumo**\n- Não informado\n"
            "**Subtópicos**\n1. **Não informado**\n   - Não informado\n"
            "**Termos-chave**\n" + lines
        )
