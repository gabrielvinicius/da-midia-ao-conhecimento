from __future__ import annotations

from dataclasses import dataclass, field
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
    # Descrições de quadros do vídeo ("[mm:ss] texto"), feitas no processamento.
    visual_context: List[str] = field(default_factory=list)


class TranscriptionQueryPort(Protocol):
    """Port for retrieving transcription and media data."""

    async def get_text_source(self, media_id: UUID) -> Optional[TextSourceData]:
        """Retrieves standardized text source data for a given media ID."""
        ...

    async def get_media_info(self, media_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves media metadata (file_path, storage_provider, type)."""
        ...

    async def get_media_owner(self, media_id: UUID) -> Optional[UUID]:
        """Dono da mídia, ou None se ela não existir."""
        ...

