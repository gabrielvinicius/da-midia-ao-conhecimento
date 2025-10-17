# src/transcription/application/services/transcription_processor.py
"""
Transcription Processor Service following SRP principle.
Responsible only for coordinating the transcription processing workflow.
"""
import structlog
from typing import Dict, Any

from src.transcription.domain.interfaces import SpeechRecognitionService
from src.transcription.application.services.audio_processor import AudioProcessor
from src.transcription.application.services.transcription_factory import TranscriptionFactory
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.domain.transcription import Transcription

logger = structlog.get_logger(__name__)


class TranscriptionProcessor:
    """
    Processes transcription requests using the appropriate speech recognition service.
    Follows SRP: Only responsible for transcription processing coordination.
    """
    
    def __init__(
        self,
        audio_processor: AudioProcessor,
        transcription_factory: TranscriptionFactory,
        transcription_repository: TranscriptionRepository
    ):
        self._audio_processor = audio_processor
        self._transcription_factory = transcription_factory
        self._transcription_repository = transcription_repository
    
    async def process_audio_transcription(
        self,
        media_id: str,
        audio_data: bytes,
        language: str,
        provider: str,
        speech_service: SpeechRecognitionService
    ) -> Transcription:
        """Process audio transcription using the specified speech recognition service."""
        logger.info(
            "transcription.processing.started",
            media_id=media_id,
            provider=provider,
            language=language
        )
        
        try:
            # Create transcription entity
            transcription = self._transcription_factory.create_transcription(
                media_id=media_id,
                provider=provider,
                language=language
            )
            
            # Mark as processing and save
            transcription.process()
            await self._transcription_repository.save(transcription)
            
            # Process audio if needed
            processed_audio = await self._audio_processor.process_audio(
                audio_data=audio_data,
                target_format="wav"
            )
            
            # Perform transcription
            result = await speech_service.transcribe(
                audio_data=processed_audio,
                language=language
            )
            
            # Update transcription with result
            transcription.mark_as_completed(result)
            await self._transcription_repository.save(transcription)
            
            logger.info(
                "transcription.processing.completed",
                media_id=media_id,
                transcription_id=str(transcription.id),
                text_length=len(transcription.text)
            )
            
            return transcription
            
        except Exception as e:
            logger.error(
                "transcription.processing.failed",
                media_id=media_id,
                error=str(e)
            )
            
            # Mark transcription as failed if it exists
            if 'transcription' in locals():
                transcription.mark_as_failed(str(e))
                await self._transcription_repository.save(transcription)
            
            raise
    
    async def process_video_transcription(
        self,
        media_id: str,
        video_data: bytes,
        language: str,
        provider: str,
        speech_service: SpeechRecognitionService
    ) -> Transcription:
        """Process video transcription by extracting audio first."""
        logger.info(
            "transcription.video_processing.started",
            media_id=media_id,
            provider=provider,
            language=language
        )
        
        # Extract audio from video
        audio_data = await self._audio_processor.extract_audio_from_video(video_data)
        
        # Process as audio transcription
        return await self.process_audio_transcription(
            media_id=media_id,
            audio_data=audio_data,
            language=language,
            provider=provider,
            speech_service=speech_service
        )