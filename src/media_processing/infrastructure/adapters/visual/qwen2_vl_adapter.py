"""Adaptador para o modelo multimodal Qwen2.5-VL (SOTA)."""
from __future__ import annotations

import asyncio
import io
import torch
import structlog
from PIL import Image

from src.media_processing.application.ports import VisualAnalysisPort
from src.shared.infrastructure.config.settings import settings

logger = structlog.get_logger(__name__)

class Qwen2VLAdapter(VisualAnalysisPort):
    """
    Implementa visão computacional e raciocínio multimodal usando Qwen2.5-VL-7B-Instruct.
    Utiliza quantização 4-bit para caber em GPUs de 12GB VRAM (Consumer Grade).
    """

    def __init__(self, model_id: str = "Qwen/Qwen2.5-VL-7B-Instruct"):
        self.model_id = model_id
        self.device = settings.resolved_device
        self._model = None
        self._processor = None
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            try:
                from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
                from qwen_vl_utils import process_vision_info  # noqa: F401 (exigido pelo modelo)
                
                logger.info(
                    "qwen2_vl.loading_model", 
                    device=self.device, 
                    model=self.model_id,
                    quantization="4bit"
                )
                
                # Configuração de Quantização 4-bit (NF4) para eficiência de VRAM
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    bnb_4bit_use_double_quant=True
                )

                # Carregamento do Modelo
                self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    self.model_id,
                    torch_dtype="auto",
                    device_map="auto",
                    quantization_config=bnb_config if self.device == "cuda" else None
                ).eval()

                # Processador (Imagem + Texto)
                self._processor = AutoProcessor.from_pretrained(self.model_id)
                self._initialized = True
                
            except ImportError as e:
                logger.error("qwen2_vl.dependency_missing", error=str(e))
                raise RuntimeError(
                    "Qwen2-VL requires 'transformers>=4.45', 'accelerate', 'bitsandbytes' and 'qwen-vl-utils'. "
                    "Install them with: pip install qwen-vl-utils bitsandbytes accelerate git+https://github.com/huggingface/transformers"
                ) from e

    async def release(self) -> None:
        """Descarrega o modelo e devolve a memória da GPU ao driver."""
        self._model = None
        self._processor = None
        self._initialized = False
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            logger.warning("qwen2_vl.release_failed", error=str(exc))

    async def describe_frame(self, frame_bytes: bytes, prompt: str = "Describe this image in detail.") -> str:
        """
        Analisa um único frame.
        Nota: Qwen2-VL suporta vídeo nativo, mas esta interface mantém compatibilidade com o pipeline atual.
        """
        def _sync_inference():
            self._initialize()
            from qwen_vl_utils import process_vision_info

            # Carregar imagem em memória
            image = Image.open(io.BytesIO(frame_bytes))

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # Preparar inputs
            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self._processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            
            inputs = inputs.to(self._model.device)

            # Geração
            generated_ids = self._model.generate(**inputs, max_new_tokens=256)
            
            # Trim inputs from output
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            
            output_text = self._processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            
            return output_text[0]

        try:
            return await asyncio.to_thread(_sync_inference)
        except Exception as exc:
            logger.error("qwen2_vl.inference_failed", error=str(exc))
            return "Visual description unavailable."

__all__ = ["Qwen2VLAdapter"]
