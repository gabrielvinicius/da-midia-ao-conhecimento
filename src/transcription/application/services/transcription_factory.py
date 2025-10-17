# src/transcription/application/services/transcription_factory.py
"""
Transcription Factory Service following SRP principle.
Responsible only for creating transcription entities.
"""
from typing import Dict, Any
from uuid import UUID

from src.transcription.domain.transcription import Transcription, TranscriptionStatus


class TranscriptionFactory:
    """Factory for creating transcription entities."""
    
    def create_transcription(
        self,
        media_id: UUID,
        provider: str = None,
        language: str = None
    ) -> Transcription:
        """Create a new transcription entity."""
        transcription = Transcription()
        transcription.media_id = media_id
        transcription.provider = provider
        transcription.status = TranscriptionStatus.PENDING
        return transcription
    
    def create_from_result(
        self,
        media_id: UUID,
        provider: str,
        result: Dict[str, Any],
        language: str = None
    ) -> Transcription:
        """Create a completed transcription from AI provider result."""
        transcription = self.create_transcription(media_id, provider, language)
        transcription.mark_as_completed(result)
        return transcription