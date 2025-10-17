# src/transcription/application/services/transcription_orchestrator.py
"""
Transcription orchestrator implementation - DIP compliance.
"""
from typing import Optional
import structlog

from src.transcription.domain.interfaces import (
    TranscriptionOrchestrator,
    ITranscriptionRepository,
    TranscriptionStateManager
)
from src.transcription.domain.transcription import Transcription
from src.transcription.domain.services.transcription_coordinator import TranscriptionCoordinator

logger = structlog.get_logger(__name__)


class TranscriptionOrchestratorImpl(TranscriptionOrchestrator):
    """
    High-level orchestrator for transcription operations.
    Follows DIP - depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        repository: ITranscriptionRepository,
        state_manager: TranscriptionStateManager,
        coordinator: TranscriptionCoordinator
    ):
        self._repository = repository
        self._state_manager = state_manager
        self._coordinator = coordinator
    
    async def process_transcription(
        self, 
        media_id: str, 
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Process complete transcription workflow."""
        logger.info(
            "transcription.orchestrator.start",
            media_id=media_id,
            language=language,
            provider=provider,
            user_id=user_id,
            audio_size=len(audio_data)
        )
        
        # Check if already processing
        if await self._state_manager.is_processing(media_id):
            existing_transcription = await self._state_manager.get_transcription_state(media_id)
            logger.warning(
                "transcription.orchestrator.already_processing",
                media_id=media_id,
                transcription_id=str(existing_transcription.id) if existing_transcription else None
            )
            return existing_transcription
        
        transcription = None
        try:
            # 1. Start processing
            transcription = await self._state_manager.start_processing(
                media_id=media_id,
                language=language,
                provider=provider
            )
            
            # 2. Perform transcription through coordinator
            result = await self._coordinator.transcribe_audio(
                media_id=media_id,
                audio_data=audio_data,
                language=language,
                user_id=user_id
            )
            
            # 3. Complete processing
            transcription = await self._state_manager.complete_processing(
                transcription=transcription,
                result=result
            )
            
            logger.info(
                "transcription.orchestrator.completed",
                media_id=media_id,
                transcription_id=str(transcription.id),
                text_length=len(result.get("text", ""))
            )
            
            return transcription
            
        except Exception as e:
            logger.error(
                "transcription.orchestrator.failed",
                media_id=media_id,
                error=str(e),
                transcription_id=str(transcription.id) if transcription else None
            )
            
            # Handle failure
            if transcription:
                transcription = await self._state_manager.fail_processing(
                    transcription=transcription,
                    error=str(e)
                )
            
            raise
    
    async def process_video_transcription(
        self, 
        media_id: str, 
        video_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Process video transcription workflow."""
        logger.info(
            "transcription.orchestrator.video_start",
            media_id=media_id,
            language=language,
            provider=provider,
            video_size=len(video_data)
        )
        
        transcription = None
        try:
            # 1. Start processing
            transcription = await self._state_manager.start_processing(
                media_id=media_id,
                language=language,
                provider=provider
            )
            
            # 2. Process video through coordinator
            result = await self._coordinator.process_video_audio(
                media_id=media_id,
                video_data=video_data,
                language=language,
                user_id=user_id
            )
            
            # 3. Complete processing
            transcription = await self._state_manager.complete_processing(
                transcription=transcription,
                result=result
            )
            
            logger.info(
                "transcription.orchestrator.video_completed",
                media_id=media_id,
                transcription_id=str(transcription.id)
            )
            
            return transcription
            
        except Exception as e:
            logger.error(
                "transcription.orchestrator.video_failed",
                media_id=media_id,
                error=str(e),
                transcription_id=str(transcription.id) if transcription else None
            )
            
            if transcription:
                transcription = await self._state_manager.fail_processing(
                    transcription=transcription,
                    error=str(e)
                )
            
            raise
    
    async def get_transcription(self, media_id: str) -> Optional[Transcription]:
        """Get existing transcription."""
        return await self._state_manager.get_transcription_state(media_id)
    
    async def retry_failed_transcription(
        self, 
        media_id: str, 
        audio_data: bytes,
        language: str,
        provider: str,
        user_id: str
    ) -> Transcription:
        """Retry failed transcription."""
        logger.info(
            "transcription.orchestrator.retry",
            media_id=media_id,
            provider=provider
        )
        
        # Reset failed transcription
        await self._state_manager.reset_failed_transcription(media_id)
        
        # Process again
        return await self.process_transcription(
            media_id=media_id,
            audio_data=audio_data,
            language=language,
            provider=provider,
            user_id=user_id
        )
    
    async def get_transcription_status(self, media_id: str) -> Optional[str]:
        """Get current transcription status."""
        transcription = await self._repository.find_by_media_id(media_id)
        return transcription.status.value if transcription else None
    
    async def delete_transcription(self, media_id: str) -> bool:
        """Delete transcription for media."""
        logger.info("transcription.orchestrator.delete", media_id=media_id)
        
        transcription = await self._state_manager.get_transcription_state(media_id)
        if transcription:
            return await self._repository.delete(transcription.id)
        
        return False
    
    async def update_speaker_aliases(
        self, 
        media_id: str, 
        aliases: dict[str, str]
    ) -> Optional[Transcription]:
        """Update speaker aliases for transcription."""
        logger.info(
            "transcription.orchestrator.update_speakers",
            media_id=media_id,
            aliases=aliases
        )
        
        transcription = await self._state_manager.get_transcription_state(media_id)
        if transcription:
            transcription.set_speaker_aliases(aliases)
            return await self._repository.save(transcription)
        
        return None
    
    async def get_provider_capabilities(self) -> dict:
        """Get current provider capabilities."""
        try:
            return await self._coordinator.get_provider_capabilities()
        except Exception:
            return {"error": "Unable to get provider capabilities"}