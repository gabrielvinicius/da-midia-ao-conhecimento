"""Faster-Whisper adapter for high-performance transcription."""
from __future__ import annotations

import logging
from typing import BinaryIO

from src.media_processing.application.ports.transcription import TranscriptionPort, TranscriptionResult, TranscriptionSegment
from src.shared.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

class FasterWhisperAdapter(TranscriptionPort):
    def __init__(self, model_size: str = "large-v3-turbo", device: str | None = None, compute_type: str = "float16"):
        self.model_size = model_size
        self.device = device or ("cuda" if settings.ai_device == "cuda" else "cpu")
        self.compute_type = compute_type
        self._model = None

    def _get_model(self):
        if not self._model:
            try:
                from faster_whisper import WhisperModel
                logger.info("faster_whisper.loading_model", size=self.model_size, device=self.device)
                self._model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type
                )
            except Exception as e:
                logger.error("faster_whisper.load_failed", error=str(e))
                raise
        return self._model

    async def transcribe(self, audio_file: BinaryIO, language: str | None = None) -> TranscriptionResult:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        model = self._get_model()
        
        # Faster-whisper accepts file path or binary stream
        segments, info = model.transcribe(
            audio_file, 
            language=language,
            beam_size=5,
            word_timestamps=True
        )

        # Convert generator to list
        segment_list = list(segments)
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        # Calculate duration
        duration = info.duration
        
        # Build Transcript
        full_text = "".join([s.text for s in segment_list]).strip()
        
        domain_segments = [
            TranscriptionSegment(
                id=str(i),
                text=s.text.strip(),
                start=s.start,
                end=s.end,
                confidence=getattr(s, "avg_logprob", 0.0), # Approximate confidence
                speaker=None 
            )
            for i, s in enumerate(segment_list)
        ]

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            duration=duration,
            segments=domain_segments,
            confidence=0.95, # High confidence for large-v3
            provider="faster-whisper"
        )
