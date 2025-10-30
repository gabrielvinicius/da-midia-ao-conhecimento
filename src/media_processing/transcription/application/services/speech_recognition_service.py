"""High-level speech recognition service used in tests."""
from __future__ import annotations

import time
from typing import Dict, Mapping, Optional
from uuid import UUID


class SpeechRecognitionService:
    def __init__(
        self,
        *,
        speech_recognition_provider,
        validator,
        metrics_service,
        state_manager,
    ) -> None:
        self._provider = speech_recognition_provider
        self._validator = validator
        self._metrics = metrics_service
        self._state = state_manager

    async def transcribe(
        self,
        audio: bytes,
        *,
        language: str,
        transcription_id: Optional[UUID] = None,
    ) -> str:
        self._validator.validate(audio, language)
        cache_key = str(transcription_id) if transcription_id is not None else None
        if cache_key:
            cached = await self._state.get(cache_key)
            if cached:
                return cached

        start = time.monotonic()
        try:
            result = await self._provider.transcribe(audio, language=language)
            success = True
        except Exception:
            success = False
            raise
        finally:
            if self._metrics is not None:
                self._metrics.record_transcription(
                    success=success,
                    duration=time.monotonic() - start,
                )

        if cache_key:
            await self._state.set(cache_key, result)
        return result

    async def batch_transcribe(
        self,
        audio_batches: Mapping[UUID, bytes],
        *,
        language: str,
    ) -> Dict[UUID, str]:
        results: Dict[UUID, str] = {}
        for key, payload in audio_batches.items():
            results[key] = await self.transcribe(payload, language=language, transcription_id=key)
        return results
