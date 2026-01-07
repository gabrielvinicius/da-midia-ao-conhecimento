"""Adaptador para o modelo multimodal Moondream 2."""
from __future__ import annotations

import asyncio
import io
import structlog
from typing import Optional
from src.media_processing.application.ports import VisualAnalysisPort
from src.shared.infrastructure.config.settings import settings

logger = structlog.get_logger(__name__)

class MoondreamVisualAdapter(VisualAnalysisPort):
    """Implementa visão computacional leve usando Moondream 2."""

    def __init__(self, model_id: str = "vikhyatk/moondream2", revision: str = "2024-08-26"):
        self.model_id = model_id
        self.revision = revision
        self.device = settings.resolved_device
        self._model = None
        self._tokenizer = None
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from PIL import Image
            
            logger.info("moondream.loading_model", device=self.device, model=self.model_id)
            
            # Moondream 2 é pequeno o suficiente para carregar rápido na GPU
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id, 
                trust_remote_code=True, 
                revision=self.revision,
                device_map={"": self.device} if self.device == "cuda" else "cpu"
            ).eval()
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.revision)
            self._initialized = True

    async def describe_frame(self, frame_bytes: bytes, prompt: str = "Describe this scene in detail.") -> str:
        """Executa a inferência multimodal no frame."""
        from PIL import Image
        
        def _sync_inference():
            self._initialize()
            image = Image.open(io.BytesIO(frame_bytes))
            enc_image = self._model.encode_image(image)
            return self._model.answer_question(enc_image, prompt, self._tokenizer)

        try:
            # Nível 6.0: Não bloqueia o event loop durante a inferência da GPU
            description = await asyncio.to_thread(_sync_inference)
            return description.strip()
        except Exception as exc:
            logger.error("moondream.inference_failed", error=str(exc))
            return "Visual description unavailable."

__all__ = ["MoondreamVisualAdapter"]
