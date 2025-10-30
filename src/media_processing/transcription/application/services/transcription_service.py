# src/transcription/application/transcription_service.py
"""
Consolidated Transcription Service. This single service now handles all logic
related to transcription, including processing, audio manipulation, speaker aliases,
and state management, removing the need for fragmented services and handlers.
"""
import structlog
import time
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.media_processing.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_processing.transcription.infrastructure.speech_recognizer import WhisperSpeechRecognizer
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.media_processing.transcription.infrastructure.logging import StructuredTranscriptionLogger
from src.media_processing.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics

logger = structlog.get_logger(__name__)


class TranscriptionService:
    """
    Consolidated service for all transcription operations.
    """
    
    def __init__(
        self,
        transcription_repo: TranscriptionRepository,
        speech_recognizer: WhisperSpeechRecognizer,
        storage_service: S3StorageService,
        transcription_logger: StructuredTranscriptionLogger,
        transcription_metrics: PrometheusTranscriptionMetrics,
        target_sample_rate: int = 16000
    ):
        self.repo = transcription_repo
        self.recognizer = speech_recognizer
        self.storage = storage_service
        self.logger = transcription_logger
        self.metrics = transcription_metrics
        self.target_sample_rate = target_sample_rate
        self.supported_languages = {"en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"}

    # === Core Transcription Workflow ===

    async def process_transcription(self, media_id: str, file_path: str, language: str, provider: str) -> Transcription:
        """The main method to process a transcription request."""
        start_time = time.monotonic()
        success = False
        error = None
        transcription_id = None

        logger.info("transcription.process.started", media_id=media_id, provider=provider)
        try:
            # 1. Download and process audio
            audio_data = await self.storage.download_file(file_path)
            normalized_audio = await self._normalize_audio(audio_data)

            # 2. Create transcription record
            transcription = Transcription(
                media_id=UUID(media_id),
                provider=provider
            )
            transcription.process()
            await self.repo.add(transcription)
            transcription_id = transcription.id

            # 3. Perform speech recognition
            transcription_result = await self.recognizer.transcribe(
                audio_data=normalized_audio,
                language=language,
                options={"provider": provider}
            )

            # 4. Update record with results
            transcription.mark_as_completed(transcription_result)
            await self.repo.update(transcription)
            success = True
            logger.info("transcription.process.completed", transcription_id=str(transcription_id))
            return transcription

        except Exception as e:
            error = e
            logger.error("transcription.process.failed", media_id=media_id, error=str(e))
            if transcription_id:
                transcription = await self.repo.get_by_id(transcription_id)
                if transcription:
                    transcription.mark_as_failed(str(e))
                    await self.repo.update(transcription)
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.logger.log_operation(
                operation="process_transcription",
                media_id=media_id,
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            # Metrics recording can be added here

    async def set_speaker_aliases(self, transcription_id: UUID, aliases: Dict[str, str]) -> Transcription:
        """Sets speaker aliases for a given transcription."""
        logger.info("transcription.set_aliases.started", transcription_id=str(transcription_id))
        self._validate_speaker_aliases(aliases)
        
        transcription = await self.repo.get_by_id(transcription_id)
        if not transcription:
            raise ValueError(f"Transcription with ID {transcription_id} not found.")

        transcription.set_speaker_aliases(aliases)
        await self.repo.update(transcription)
        logger.info("transcription.set_aliases.completed", transcription_id=str(transcription_id))
        return transcription

    # === Query Methods ===

    async def get_transcription_by_id(self, transcription_id: UUID) -> Optional[Transcription]:
        return await self.repo.get_by_id(transcription_id)

    async def get_transcription_by_media_id(self, media_id: UUID) -> Optional[Transcription]:
        return await self.repo.get_by_media_id(media_id)

    # === Private Helper Methods ===

    async def _normalize_audio(self, audio_data: bytes) -> bytes:
        """Normalize audio to a standard format for transcription."""
        command = [
            'ffmpeg',
            '-i', 'pipe:0',
            '-f', 'wav',
            '-ac', '1',  # Mono
            '-ar', str(self.target_sample_rate),  # Target sample rate
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-loglevel', 'error',
            'pipe:1'
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=audio_data)
        if process.returncode != 0:
            logger.error("audio.normalization.failed", error=stderr.decode())
            raise RuntimeError("Audio normalization failed.")
        return stdout

    def _validate_language(self, language: str) -> None:
        if language not in self.supported_languages:
            raise ValueError(f"Language '{language}' not supported. Supported: {self.supported_languages}")

    def _validate_speaker_aliases(self, aliases: Dict[str, str]) -> None:
        if not aliases:
            raise ValueError("Speaker aliases cannot be empty")
        for speaker_id, alias in aliases.items():
            if not all([speaker_id, isinstance(speaker_id, str), alias, isinstance(alias, str), len(alias) <= 100]):
                raise ValueError("Invalid speaker alias format")