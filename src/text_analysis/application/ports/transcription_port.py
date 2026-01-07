from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID


@dataclass
class TextSourceData:
    """Standardized DTO for text source data consumed by analysis."""
    
    id: UUID
    text: str
    language: str
    segments: List[Dict[str, Any]]
    media_id: UUID


class TranscriptionQueryPort(Protocol):
    """Port for retrieving transcription and media data."""

    async def get_text_source(self, media_id: UUID) -> Optional[TextSourceData]:
        """Retrieves standardized text source data for a given media ID."""
        ...

    async def get_media_info(self, media_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves media metadata (file_path, storage_provider, type)."""
        ...

