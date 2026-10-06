"""Adaptador para o modelo multimodal Moondream 2."""
from __future__ import annotations

import asyncio
import io
import structlog
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
            
            logger.info("moondream.loading_model", device=self.device, model=self.model_id)
            
            import torch

            # Na GPU, float16: sem torch_dtype o modelo carregava em float32,
            # o dobro de memória (~7 GB) numa placa de 12 GB compartilhada.
            on_gpu = self.device == "cuda"
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                trust_remote_code=True,
                revision=self.revision,
                torch_dtype=torch.float16 if on_gpu else torch.float32,
                device_map={"": self.device} if on_gpu else "cpu",
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

    async def release(self) -> None:
        """Descarrega o modelo e devolve a memória da GPU ao driver, para o
        Ollama usá-la nas etapas seguintes; a próxima análise o recarrega."""
        self._model = None
        self._tokenizer = None
        self._initialized = False
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            logger.warning("moondream.release_failed", error=str(exc))

__all__ = ["MoondreamVisualAdapter"]
