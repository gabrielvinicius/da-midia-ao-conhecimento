"""Transcrição com Faster-Whisper (CTranslate2).

Até esta versão, o adaptador importava um módulo inexistente e nunca era
carregado: o sistema caía no openai-whisper com o modelo "base".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from src.media_processing.application.ports import SpeechRecognizer
from src.shared.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


def resolve_device_and_compute(
    requested_device: str, requested_compute: str, cuda_devices: int
) -> tuple[str, str]:
    """Dispositivo e precisão que o CTranslate2 consegue usar.

    O CTranslate2 (base do Faster-Whisper) só usa GPU NVIDIA. Em máquinas
    sem ela, incluindo GPUs AMD, a transcrição roda na CPU. Na CPU, float16
    não é aceito; usa-se int8.
    """
    device = (requested_device or "auto").lower()
    wants_gpu = device in {"auto", "cuda", "rocm", "gpu"}
    device = "cuda" if wants_gpu and cuda_devices > 0 else "cpu"

    compute = (requested_compute or "default").lower()
    if compute == "default":
        compute = "float16" if device == "cuda" else "int8"
    if device == "cpu" and "float16" in compute:
        compute = "int8"
    return device, compute


def glossary_prompt(terms: str | None) -> str | None:
    """O glossário como frase pontuada, ou None se não houver termos.

    O Whisper imita o estilo do texto que recebe como contexto. Medido numa
    aula de 30 min: a lista crua de termos derrubou os pontos finais de 315
    para 211 e criou 14 laços de repetição ("em 2021, em 2021, …"); escrita
    como frase, e sem condicionar cada trecho no anterior, ficaram 253 pontos e
    nenhum laço, com os termos do glossário escritos certo.
    """
    terms = (terms or "").strip().rstrip(".")
    return f"Nesta gravação, falamos de {terms}." if terms else None


def _cuda_device_count() -> int:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count()
    except Exception:
        return 0


class FasterWhisperAdapter(SpeechRecognizer):
    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        hotwords: str | None = None,
    ) -> None:
        self.model_size = model_size or settings.whisper_model
        # Glossário do domínio (WHISPER_HOTWORDS): favorece a grafia certa dos
        # termos técnicos que o modelo erra.
        self.hotwords = glossary_prompt(hotwords if hotwords is not None else settings.whisper_hotwords)
        self.device, self.compute_type = resolve_device_and_compute(
            device or settings.ai_device,
            compute_type or settings.ai_compute_type,
            _cuda_device_count(),
        )
        self.model_label = f"faster-whisper {self.model_size}"
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                "faster_whisper.loading_model size=%s device=%s compute_type=%s",
                self.model_size, self.device, self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        return self._model

    def _transcribe_sync(self, path: str, language: str | None) -> Dict[str, Any]:
        segments, info = self._get_model().transcribe(
            path,
            language=language,
            beam_size=5,
            # Pula trechos sem fala; reduz textos inventados em silêncios.
            vad_filter=True,
            hotwords=self.hotwords,
            # Com glossário, um trecho errado contaminava os seguintes (laços de
            # repetição); sem glossário, mantém o padrão do modelo.
            condition_on_previous_text=self.hotwords is None,
        )
        items = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "confidence": seg.avg_logprob,
            }
            for seg in segments  # o gerador só transcreve ao ser percorrido
        ]
        return {
            "text": " ".join(item["text"] for item in items).strip(),
            "language": info.language,
            "provider": "faster-whisper",
            "segments": items,
            "duration": info.duration,
        }

    async def transcribe(self, path: str, language: str = "auto") -> Dict[str, Any]:
        lang = None if not language or language.lower() == "auto" else language
        return await asyncio.to_thread(self._transcribe_sync, path, lang)


__all__ = ["FasterWhisperAdapter", "resolve_device_and_compute"]
