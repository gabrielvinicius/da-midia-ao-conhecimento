# src/transcription/domain/services/transcription_coordinator.py
"""
Domain service for coordinating transcription operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from src.transcription.domain.interfaces import (
    SpeechRecognitionProvider,
    AudioProcessor,
    TranscriptionValidator,
    TranscriptionOperationLogger,
    TranscriptionMetrics,
    TranscriptionNotificationService
)


class TranscriptionOperationError(Exception):
    """Domain exception for transcription operation errors."""
    pass


class TranscriptionCoordinator:
    """
    Domain service that coordinates transcription operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        provider: SpeechRecognitionProvider,
        audio_processor: AudioProcessor,
        validator: TranscriptionValidator,
        logger: TranscriptionOperationLogger,
        metrics: TranscriptionMetrics,
        notification_service: TranscriptionNotificationService
    ):
        self._provider = provider
        self._audio_processor = audio_processor
        self._validator = validator
        self._logger = logger
        self._metrics = metrics
        self._notification_service = notification_service
    
    async def transcribe_audio(
        self, 
        media_id: str,
        audio_data: bytes,
        language: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Transcribe audio with complete workflow coordination."""
        start_time = datetime.utcnow()
        success = False
        error = None
        audio_duration = 0.0
        result_length = 0
        
        try:
            # Notify processing started
            await self._notification_service.notify_started(media_id, user_id, language)
            
            # Validate and process audio
            if not await self._audio_processor.validate_audio(audio_data):
                raise TranscriptionOperationError("Invalid audio data")
            
            # Extract audio information
            audio_info = await self._audio_processor.extract_audio_info(audio_data)
            audio_duration = audio_info.get("duration", 0.0)
            
            # Normalize audio for transcription
            processed_audio = await self._audio_processor.normalize_audio(audio_data)
            
            # Validate language
            if not await self._validator.validate_language(language):
                # Auto-detect language if invalid
                language = "auto"
            
            # Perform transcription
            result = await self._provider.transcribe(processed_audio, language)
            
            # Validate transcription result
            if not await self._validator.validate_result(result):
                raise TranscriptionOperationError("Invalid transcription result")
            
            # Calculate result metrics
            result_length = len(result.get("text", ""))
            
            # Notify completion
            await self._notification_service.notify_completed(media_id, user_id, result)
            
            success = True
            return result
            
        except Exception as e:
            error = e
            success = False
            
            # Notify failure
            await self._notification_service.notify_failed(media_id, user_id, str(e))
            
            raise TranscriptionOperationError(
                f"Failed to transcribe audio for media {media_id}: {e}"
            ) from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="transcribe",
                media_id=media_id,
                provider=self._provider.provider_name,
                language=language,
                success=success,
                duration=duration,
                audio_duration=audio_duration,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation="transcribe",
                provider=self._provider.provider_name,
                language=language,
                duration=duration,
                success=success,
                audio_duration=audio_duration,
                result_length=result_length
            )
    
    async def process_video_audio(
        self, 
        media_id: str,
        video_data: bytes,
        language: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Extract audio from video and transcribe."""
        try:
            # Extract audio from video
            audio_data = await self._audio_processor.extract_audio_from_video(video_data)
            
            # Process as normal audio
            return await self.transcribe_audio(media_id, audio_data, language, user_id)
            
        except Exception as e:
            raise TranscriptionOperationError(
                f"Failed to process video audio for media {media_id}: {e}"
            ) from e
    
    async def update_processing_progress(
        self, 
        media_id: str, 
        user_id: str, 
        progress: float
    ) -> None:
        """Update processing progress with error handling."""
        try:
            await self._notification_service.notify_progress(media_id, user_id, progress)
        except Exception as e:
            # Log progress notification failure but don't propagate
            await self._logger.log_operation(
                operation="progress_notification",
                media_id=media_id,
                provider=self._provider.provider_name,
                language="unknown",
                success=False,
                duration=0.0,
                error=e
            )
    
    async def get_provider_capabilities(self) -> Dict[str, Any]:
        """Get current provider capabilities."""
        try:
            return await self._provider.get_capabilities()
        except Exception:
            return {"provider_name": self._provider.provider_name}