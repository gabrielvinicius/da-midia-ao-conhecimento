import io
import os
import tempfile
from typing import Dict

import av
import numpy as np
import resampy
import structlog
from src.media_processing.transcription.infrastructure.dependencies import (
    register_speech_recognition,
)
from transformers import pipeline

logger = structlog.get_logger(__name__)


@register_speech_recognition("huggingface")
class HuggingfaceTranscriber:
    def __init__(self, model_name: str = "openai/whisper-base"):
        self.model_name = model_name
        self._model = None
        self._initialized = False
        self.sample_rate = 16000  # Whisper expects 16kHz audio

    def _get_model(self):
        if not self._initialized:
            from transformers import pipeline
            self._model = pipeline(task="automatic-speech-recognition", model=self.model_name)
            self._initialized = True
        return self._model

    @property
    def provider_name(self) -> str:
        return "huggingface"

    async def transcribe(self, file: bytes, language: str = "en") -> Dict[str, object]:
        path = None
        try:
            model = self._get_model()
            path = await self._decode_file_bytes(file)
            # The Hugging Face pipeline can use the language if the model supports it
            result = model(path, generate_kwargs={"language": language})
            text = result["text"].strip()
            return {
                "text": text,
                "segments": None,
                "language": language,
                "provider": self.provider_name,
            }
        except Exception as e:
            logger.error(
                "huggingface.transcription_failed",
                error=str(e),
                exc_info=True,
            )
            raise RuntimeError(f"Erro de transcrição (huggingface): {str(e)}")
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

    async def _decode_audio_bytes(self, file_bytes: bytes) -> np.ndarray:
        """Decodes audio or audio-track-from-video to float32 mono 16kHz"""
        try:
            buffer = io.BytesIO(file_bytes)
            container = av.open(buffer)

            audio_stream = next(
                (s for s in container.streams if s.type == "audio"), None
            )
            if audio_stream is None:
                raise ValueError("Nenhuma trilha de áudio encontrada no arquivo de entrada")

            frames = []
            for packet in container.demux(audio_stream):
                for frame in packet.decode():
                    samples = frame.to_ndarray()
                    if samples.ndim > 1:
                        samples = np.mean(samples, axis=0)  # Convert to mono
                    frames.append(samples)

            if not frames:
                raise ValueError("Nenhum frame de áudio encontrado")

            audio = np.concatenate(frames).astype(np.float32)
            original_rate = audio_stream.rate

            if original_rate != self.sample_rate:
                audio = resampy.resample(audio, original_rate, self.sample_rate)

            audio /= np.max(np.abs(audio)) + 1e-9  # Normalize

            return audio

        except Exception as e:
            logger.error("huggingface.audio_decode_failed", error=str(e))
            raise RuntimeError(f"Erro ao decodificar áudio: {str(e)}")

    async def _decode_file_bytes(self, file_bytes: bytes) -> str:
        tmp = tempfile.NamedTemporaryFile(suffix=".tmp", delete=False)
        tmp.write(file_bytes)
        tmp.flush()
        tmp.close()
        return tmp.name
