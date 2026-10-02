"""Adaptador para o modelo de TTS Kokoro-82M (via ONNX)."""
from __future__ import annotations

import asyncio
import io
import structlog

from src.media_processing.application.ports.tts_port import TTSProviderPort

logger = structlog.get_logger(__name__)

class KokoroTTSAdapter(TTSProviderPort):
    """
    Implementa Text-to-Speech usando Kokoro-82M.
    É extremamente leve (~80MB) e rápido, ideal para CPU ou GPU.
    """

    def __init__(self, model_path: str = "kokoro-v0_19.onnx", voices_path: str = "voices.json"):
        self.model_path = model_path
        self.voices_path = voices_path
        self._kokoro = None
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            try:
                from kokoro_onnx import Kokoro
                import soundfile as sf  # noqa: F401 (dependência exigida pelo Kokoro)
                
                # Em um cenário real, garantiríamos o download do modelo .onnx e voices.json
                # Aqui assumimos que eles estão no cache ou no diretório de assets
                # Para simplificar o "start", podemos usar um caminho padrão ou baixar sob demanda
                
                logger.info("kokoro.initializing", model=self.model_path)
                
                # Placeholder para lógica de download automático dos pesos ONNX se não existirem
                # self._ensure_model_exists() 

                self._kokoro = Kokoro(self.model_path, self.voices_path)
                self._initialized = True
                
            except ImportError as e:
                logger.error("kokoro.dependency_missing", error=str(e))
                raise RuntimeError(
                    "Kokoro TTS requires 'kokoro-onnx' and 'soundfile'. "
                    "Install with: pip install kokoro-onnx soundfile"
                ) from e
            except Exception as e:
                logger.warning("kokoro.init_failed", error=str(e))
                # Fallback ou re-raise dependendo da política de erro

    async def generate_audio(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
        def _sync_generate():
            self._initialize()
            if not self._kokoro:
                raise RuntimeError("Kokoro model not initialized")

            # Kokoro ONNX retorna samples e sample_rate
            samples, sample_rate = self._kokoro.create(
                text, voice=voice, speed=speed, lang="en-us"
            )
            
            # Converter para bytes (WAV)
            buffer = io.BytesIO()
            import soundfile as sf
            sf.write(buffer, samples, sample_rate, format="WAV")
            return buffer.getvalue()

        try:
            return await asyncio.to_thread(_sync_generate)
        except Exception as exc:
            logger.error("kokoro.generation_failed", error=str(exc))
            raise

__all__ = ["KokoroTTSAdapter"]
