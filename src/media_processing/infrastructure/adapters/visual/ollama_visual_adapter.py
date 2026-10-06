"""Descrição de quadros de vídeo com um modelo multimodal servido pelo Ollama."""
from __future__ import annotations

import base64

import httpx
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_PROMPT = (
    "Descreva de forma objetiva, em português, o que aparece nesta imagem de um vídeo: "
    "textos, gráficos, fórmulas, slides, pessoas e ações. Não invente o que não estiver visível."
)


class OllamaVisualAdapter:
    """Implementa VisualAnalysisPort usando /api/chat com imagem em base64.

    Permite usar o mesmo modelo do resumo (ex.: Qwen3.5-9B, que aceita imagens)
    para descrever os quadros, sem carregar um segundo modelo de visão na GPU.
    """

    def __init__(self, model: str, host: str, timeout: int = 300) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    async def describe_frame(self, frame_bytes: bytes, prompt: str = DEFAULT_PROMPT) -> str:
        # O prompt padrão do pipeline é em inglês (pensado para o Moondream);
        # com o Ollama, usamos a instrução em português.
        if not prompt or prompt.lower().startswith("describe"):
            prompt = DEFAULT_PROMPT
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(frame_bytes).decode("ascii")],
                }
            ],
            "options": {"temperature": 0.1},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.host}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            return ((data.get("message") or {}).get("content") or "").strip()
        except Exception as exc:
            logger.error("ollama_visual.inference_failed", error=str(exc))
            return ""

    async def release(self) -> None:
        """Descarrega o modelo de visão do Ollama (keep_alive=0)."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(f"{self.host}/api/generate", json={"model": self.model, "keep_alive": 0})
        except Exception as exc:
            logger.warning("ollama_visual.release_failed", error=str(exc))


__all__ = ["OllamaVisualAdapter"]
