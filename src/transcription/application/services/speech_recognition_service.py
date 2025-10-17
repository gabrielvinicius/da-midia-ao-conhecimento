# src/transcription/application/services/speech_recognition_service.py
"""
Speech Recognition Service following SOLID principles.
Single Responsibility: Handle core transcription orchestration with validation and monitoring.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.shared.resilience.circuit_breaker import get_circuit_breaker
from src.transcription.infrastructure.interfaces import ISpeechRecognition
from src.transcription.domain.interfaces import (
    ISpeechRecognitionService,
    ITranscriptionValidator,
    ITranscriptionMetricsService,
    ITranscriptionStateManager
)

logger = structlog.get_logger(__name__)


class SpeechRecognitionService(ISpeechRecognitionService):
    """
    Core speech recognition service following SOLID principles.
    
    Single Responsibility: Orchestrate transcription workflow with validation.
    Open/Closed: Extensible through provider injection.
    Liskov Substitution: Implements ISpeechRecognitionService contract.
    Interface Segregation: Uses specific interfaces for each concern.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        speech_recognition_provider: ISpeechRecognition,
        validator: ITranscriptionValidator,
        metrics_service: ITranscriptionMetricsService,
        state_manager: ITranscriptionStateManager
    ):
        self._provider = speech_recognition_provider
        self._validator = validator
        self._metrics_service = metrics_service
        self._state_manager = state_manager

    async def transcribe(
        self, 
        audio_bytes: bytes, 
        language: str = "en",
        transcription_id: Optional[UUID] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Transcribes audio using the configured provider with validation and monitoring.
        
        Args:
            audio_bytes: Audio data to transcribe
            language: Language code for transcription
            transcription_id: Optional transcription ID for tracking
            options: Optional transcription options
            
        Returns:
            str: Transcribed text
        """
        if transcription_id:
            await self._state_manager.update_status(transcription_id, "processing")
        
        try:
            # Validate input
            self._validator.validate_audio_data(audio_bytes)
            self._validator.validate_language_code(language)
            
            # Record processing start
            if transcription_id:
                self._metrics_service.record_processing_start(transcription_id)
            
            # Apply circuit breaker protection
            breaker_key = f"transcription_{self._provider.provider_name}"
            breaker = get_circuit_breaker(breaker_key)
            
            transcribed_text = await breaker.call_async(
                self._provider.transcribe, 
                audio_bytes, 
                language=language,
                options=options or {}
            )
            
            # Validate output
            self._validator.validate_transcription_quality(transcribed_text, audio_bytes)
            
            # Record success metrics
            if transcription_id:
                self._metrics_service.record_processing_success(
                    transcription_id,
                    len(audio_bytes),
                    len(transcribed_text),
                    self._provider.provider_name
                )
                await self._state_manager.update_status(transcription_id, "completed")
            
            logger.info(
                "transcription.completed",
                transcription_id=str(transcription_id) if transcription_id else None,
                audio_size=len(audio_bytes),
                text_length=len(transcribed_text),
                provider=self._provider.provider_name,
                language=language
            )
            
            return transcribed_text
            
        except Exception as e:
            if transcription_id:
                await self._state_manager.update_status(transcription_id, "failed", str(e))
                self._metrics_service.record_processing_failure(transcription_id, str(e))
            
            logger.error(
                "transcription.failed",
                transcription_id=str(transcription_id) if transcription_id else None,
                error=str(e),
                provider=self._provider.provider_name,
                language=language
            )
            raise

    async def batch_transcribe(
        self, 
        audio_batches: Dict[UUID, bytes],
        language: str = "en",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, str]:
        """
        Transcribe multiple audio files in batch.
        
        Args:
            audio_batches: Dictionary mapping transcription IDs to audio data
            language: Language code for transcription
            options: Optional transcription options
            
        Returns:
            Dict mapping transcription IDs to transcribed text
        """
        results = {}
        failed_count = 0
        
        for transcription_id, audio_data in audio_batches.items():
            try:
                text = await self.transcribe(audio_data, language, transcription_id, options)
                results[transcription_id] = text
            except Exception as e:
                failed_count += 1
                logger.warning(
                    "transcription.batch_item_failed",
                    transcription_id=str(transcription_id),
                    error=str(e)
                )
        
        logger.info(
            "transcription.batch_completed",
            total_items=len(audio_batches),
            successful=len(results),
            failed=failed_count,
            language=language
        )
        
        return results
