# src/transcription/application/services/transcription_state_manager.py
"""
Transcription state management service - SRP compliance.
"""
from typing import Optional
import structlog
from uuid import uuid4

from src.transcription.domain.interfaces import TranscriptionStateManager, ITranscriptionRepository
from src.transcription.domain.transcription import Transcription, TranscriptionStatus

logger = structlog.get_logger(__name__)


class TranscriptionStateManagerImpl(TranscriptionStateManager):
    """
    Implementation of transcription state management.
    Follows SRP - only responsible for state transitions.
    """
    
    def __init__(self, repository: ITranscriptionRepository):
        self._repository = repository
    
    async def start_processing(
        self, 
        media_id: str, 
        language: str, 
        provider: str
    ) -> Transcription:
        """Start processing and return transcription."""
        logger.info(
            "transcription.state.start_processing",
            media_id=media_id,
            language=language,
            provider=provider
        )
        
        # Check if transcription already exists
        from uuid import UUID
        existing_transcription = await self._repository.find_by_media_id(UUID(media_id))
        
        if existing_transcription:
            # Update existing transcription
            existing_transcription.provider = provider
            existing_transcription.status = TranscriptionStatus.PROCESSING
            existing_transcription.error_message = None
            transcription = await self._repository.save(existing_transcription)
            
            logger.info(
                "transcription.state.restarted_existing",
                transcription_id=str(transcription.id),
                media_id=media_id
            )
        else:
            # Create new transcription
            transcription = Transcription(
                id=uuid4(),
                media_id=UUID(media_id),
                status=TranscriptionStatus.PROCESSING,
                provider=provider
            )
            transcription = await self._repository.save(transcription)
            
            logger.info(
                "transcription.state.created_new",
                transcription_id=str(transcription.id),
                media_id=media_id
            )
        
        return transcription
    
    async def complete_processing(
        self, 
        transcription: Transcription, 
        result: dict
    ) -> Transcription:
        """Complete processing with result."""
        logger.info(
            "transcription.state.complete_processing",
            transcription_id=str(transcription.id),
            text_length=len(result.get("text", ""))
        )
        
        # Validate state transition
        if transcription.status != TranscriptionStatus.PROCESSING:
            logger.warning(
                "transcription.state.invalid_transition",
                transcription_id=str(transcription.id),
                current_status=transcription.status.value,
                attempted_transition="complete"
            )
        
        # Update transcription with result
        transcription.mark_as_completed(result)
        updated_transcription = await self._repository.save(transcription)
        
        logger.info(
            "transcription.state.completed",
            transcription_id=str(updated_transcription.id),
            text_length=len(result.get("text", ""))
        )
        
        return updated_transcription
    
    async def fail_processing(
        self, 
        transcription: Transcription, 
        error: str
    ) -> Transcription:
        """Mark processing as failed."""
        logger.info(
            "transcription.state.fail_processing",
            transcription_id=str(transcription.id),
            error=error
        )
        
        # Truncate error message if too long
        truncated_error = error[:500] if len(error) > 500 else error
        
        # Update transcription
        transcription.mark_as_failed(truncated_error)
        updated_transcription = await self._repository.save(transcription)
        
        logger.error(
            "transcription.state.failed",
            transcription_id=str(updated_transcription.id),
            error=truncated_error
        )
        
        return updated_transcription
    
    async def update_progress(
        self, 
        transcription: Transcription, 
        progress: float
    ) -> Transcription:
        """Update processing progress."""
        logger.debug(
            "transcription.state.update_progress",
            transcription_id=str(transcription.id),
            progress=progress
        )
        
        # For now, we don't persist progress in the database
        # This could be extended to store progress if needed
        return transcription
    
    async def get_transcription_state(self, media_id: str) -> Optional[Transcription]:
        """Get current transcription state for media."""
        from uuid import UUID
        return await self._repository.find_by_media_id(UUID(media_id))
    
    async def is_processing(self, media_id: str) -> bool:
        """Check if transcription is currently processing."""
        transcription = await self.get_transcription_state(media_id)
        return transcription is not None and transcription.status == TranscriptionStatus.PROCESSING
    
    async def reset_failed_transcription(self, media_id: str) -> Optional[Transcription]:
        """Reset a failed transcription to allow reprocessing."""
        transcription = await self.get_transcription_state(media_id)
        
        if transcription and transcription.status == TranscriptionStatus.FAILED:
            transcription.status = TranscriptionStatus.PENDING
            transcription.error_message = None
            updated_transcription = await self._repository.save(transcription)
            
            logger.info(
                "transcription.state.reset",
                transcription_id=str(updated_transcription.id),
                media_id=media_id
            )
            
            return updated_transcription
        
        return None