"""
Consolidated Transcription Service
Consolidates: TranscriptionFactory, TranscriptionProcessor, TranscriptionValidator, TranscriptionStateService
"""
import structlog
from typing import Dict, Any, List, Optional, Set
from uuid import UUID

from src.transcription.domain.transcription import Transcription
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.application.commands.commands import (
    ProcessTranscriptionCommand,
    SetSpeakerAliasesCommand
)
from src.transcription.application.commands.handlers import (
    ProcessTranscriptionCommandHandler,
    SetSpeakerAliasesCommandHandler
)

logger = structlog.get_logger(__name__)


class TranscriptionService:
    """
    Consolidated service for all transcription operations.
    Handles: processing, validation, state management, speaker aliases.
    """
    
    def __init__(
        self,
        transcription_repository: TranscriptionRepository,
        process_transcription_handler: ProcessTranscriptionCommandHandler,
        set_speaker_aliases_handler: SetSpeakerAliasesCommandHandler
    ):
        self.transcription_repository = transcription_repository
        self.process_transcription_handler = process_transcription_handler
        self.set_speaker_aliases_handler = set_speaker_aliases_handler
        self.supported_languages = {"en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"}

    # === TRANSCRIPTION PROCESSING ===
    
    async def process_transcription(
        self,
        media_id: str,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Process transcription with validation."""
        # Validate language
        self._validate_language(language)
        
        command = ProcessTranscriptionCommand(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language
        )
        return await self.process_transcription_handler.handle(command)
    
    async def set_speaker_aliases(self, transcription_id: UUID, aliases: Dict[str, str]) -> Dict[str, Any]:
        """Set speaker aliases for transcription."""
        # Validate aliases
        self._validate_speaker_aliases(aliases)
        
        command = SetSpeakerAliasesCommand(
            transcription_id=transcription_id,
            aliases=aliases
        )
        return await self.set_speaker_aliases_handler.handle(command)

    # === TRANSCRIPTION VALIDATION ===
    
    def validate_audio_file(self, audio_data: bytes, min_size: int = 1024, max_size: int = 100 * 1024 * 1024) -> None:
        """Validate audio file for transcription."""
        if not audio_data:
            raise ValueError("Audio data is empty")
        
        if len(audio_data) < min_size:
            raise ValueError(f"Audio file too small (minimum {min_size} bytes)")
        
        if len(audio_data) > max_size:
            raise ValueError(f"Audio file too large (maximum {max_size} bytes)")
    
    def _validate_language(self, language: str) -> None:
        """Validate language code."""
        if language not in self.supported_languages:
            raise ValueError(f"Language '{language}' not supported. Supported: {self.supported_languages}")
    
    def _validate_speaker_aliases(self, aliases: Dict[str, str]) -> None:
        """Validate speaker aliases."""
        if not aliases:
            raise ValueError("Speaker aliases cannot be empty")
        
        for speaker_id, alias in aliases.items():
            if not speaker_id or not isinstance(speaker_id, str):
                raise ValueError("Speaker ID must be a non-empty string")
            
            if not alias or not isinstance(alias, str):
                raise ValueError("Speaker alias must be a non-empty string")
            
            if len(alias) > 100:
                raise ValueError("Speaker alias too long (maximum 100 characters)")

    # === TRANSCRIPTION FACTORY ===
    
    def create_transcription_entity(
        self,
        transcription_id: UUID,
        media_id: str,
        text: str,
        language: str,
        provider: str,
        confidence: Optional[float] = None
    ) -> Transcription:
        """Create a new Transcription entity."""
        return Transcription(
            id=transcription_id,
            media_id=UUID(media_id),
            text=text,
            language=language,
            provider=provider,
            confidence=confidence or 0.0
        )

    # === QUERY METHODS ===
    
    async def get_transcription_by_id(self, transcription_id: str) -> Optional[Transcription]:
        """Get transcription by ID."""
        return await self.transcription_repository.find_by_id(transcription_id)
    
    async def get_transcription_by_media_id(self, media_id: str) -> Optional[Transcription]:
        """Get transcription by media ID."""
        return await self.transcription_repository.find_by_media_id(media_id)
    
    async def list_transcriptions_by_user(self, user_id: str) -> List[Transcription]:
        """List transcriptions for a user."""
        return await self.transcription_repository.find_by_user_id(user_id)
    
    async def count_transcriptions(self, user_id: Optional[str] = None) -> int:
        """Count transcriptions."""
        if user_id:
            return await self.transcription_repository.count_by_user_id(user_id)
        return await self.transcription_repository.count_all()

    # === STATE MANAGEMENT ===
    
    async def update_transcription_status(self, transcription_id: str, status: str) -> Transcription:
        """Update transcription processing status."""
        transcription = await self.transcription_repository.find_by_id(transcription_id)
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        transcription.status = status
        return await self.transcription_repository.save(transcription)
    
    async def add_processing_error(self, transcription_id: str, error_message: str) -> Transcription:
        """Add error to transcription."""
        transcription = await self.transcription_repository.find_by_id(transcription_id)
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        transcription.error_message = error_message
        transcription.status = "failed"
        return await self.transcription_repository.save(transcription)

    # === STATISTICS ===
    
    async def get_transcription_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get transcription statistics."""
        if user_id:
            total = await self.count_transcriptions(user_id)
            by_language = await self.transcription_repository.count_by_user_and_language(user_id)
            by_provider = await self.transcription_repository.count_by_user_and_provider(user_id)
        else:
            total = await self.count_transcriptions()
            by_language = await self.transcription_repository.count_by_language()
            by_provider = await self.transcription_repository.count_by_provider()
        
        return {
            "total": total,
            "by_language": by_language,
            "by_provider": by_provider,
            "supported_languages": list(self.supported_languages)
        }