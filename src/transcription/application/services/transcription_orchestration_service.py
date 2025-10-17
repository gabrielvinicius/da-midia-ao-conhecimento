# src/transcription/application/services/transcription_orchestration_service.py
"""
Transcription Orchestration Service following OCP and DIP principles.
Coordinates transcription workflow without depending on concrete implementations.
"""
import structlog
from typing import Dict, Any

from src.transcription.domain.interfaces import (
    SpeechRecognitionService, 
    TranscriptionOrchestrator,
    NotificationService
)
from src.transcription.application.services.transcription_processor import TranscriptionProcessor
from src.transcription.application.services.transcription_provider_factory import TranscriptionProviderFactory
from src.transcription.application.services.transcription_metrics_service import TranscriptionMetricsService
from src.transcription.domain.transcription import Transcription

logger = structlog.get_logger(__name__)


class TranscriptionOrchestrationService(TranscriptionOrchestrator):
    """
    Orchestrates the complete transcription workflow.
    Follows OCP: Open for extension through provider factory.
    Follows DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        transcription_processor: TranscriptionProcessor,
        provider_factory: TranscriptionProviderFactory,
        metrics_service: TranscriptionMetricsService,
        notification_service: NotificationService
    ):
        self._processor = transcription_processor
        self._provider_factory = provider_factory
        self._metrics_service = metrics_service
        self._notification_service = notification_service
    
    async def process_transcription(
        self,
        media_id: str,
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Orchestrate audio transcription workflow."""
        logger.info(
            "transcription.orchestration.started",
            media_id=media_id,
            provider=provider,
            user_id=user_id
        )
        
        try:
            # Get speech recognition service
            speech_service = self._provider_factory.create_speech_service(provider)
            
            # Send processing notification
            await self._notification_service.notify_transcription_started(
                user_id=user_id,
                media_id=media_id
            )
            
            # Record metrics
            await self._metrics_service.record_transcription_started(provider)
            
            # Process transcription
            transcription = await self._processor.process_audio_transcription(
                media_id=media_id,
                audio_data=audio_data,
                language=language,
                provider=provider,
                speech_service=speech_service
            )
            
            # Send completion notification
            await self._notification_service.notify_transcription_completed(
                user_id=user_id,
                media_id=media_id,
                transcription=transcription
            )
            
            # Record success metrics
            await self._metrics_service.record_transcription_completed(
                provider=provider,
                duration=len(audio_data),  # Approximate
                text_length=len(transcription.text)
            )
            
            return transcription
            
        except Exception as e:
            # Send error notification
            await self._notification_service.notify_transcription_failed(
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
            
            # Record failure metrics
            await self._metrics_service.record_transcription_failed(provider, str(e))
            
            raise
    
    async def process_video_transcription(
        self,
        media_id: str,
        video_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Orchestrate video transcription workflow."""
        logger.info(
            "transcription.video_orchestration.started",
            media_id=media_id,
            provider=provider,
            user_id=user_id
        )
        
        try:
            # Get speech recognition service
            speech_service = self._provider_factory.create_speech_service(provider)
            
            # Send processing notification
            await self._notification_service.notify_transcription_started(
                user_id=user_id,
                media_id=media_id
            )
            
            # Record metrics
            await self._metrics_service.record_transcription_started(provider)
            
            # Process video transcription
            transcription = await self._processor.process_video_transcription(
                media_id=media_id,
                video_data=video_data,
                language=language,
                provider=provider,
                speech_service=speech_service
            )
            
            # Send completion notification
            await self._notification_service.notify_transcription_completed(
                user_id=user_id,
                media_id=media_id,
                transcription=transcription
            )
            
            # Record success metrics
            await self._metrics_service.record_transcription_completed(
                provider=provider,
                duration=len(video_data),  # Approximate
                text_length=len(transcription.text)
            )
            
            return transcription
            
        except Exception as e:
            # Send error notification
            await self._notification_service.notify_transcription_failed(
                user_id=user_id,
                media_id=media_id,
                error=str(e)
            )
            
            # Record failure metrics
            await self._metrics_service.record_transcription_failed(provider, str(e))
            
            raise