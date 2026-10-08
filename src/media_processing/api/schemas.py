# src/transcription/api/schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.media_processing.domain import TranscriptionStatus


class TranscriptionResponse(BaseModel):
    """Response schema for a transcription."""

    id: UUID
    media_id: UUID
    status: TranscriptionStatus
    provider: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    text: str
    language: Optional[str] = None
    confidence_score: Optional[float] = None
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    speaker_aliases: Dict[str, str] = Field(default_factory=dict)
    # Duração lida do arquivo (o último trecho de fala termina antes do fim).
    duration: Optional[float] = None
    # Trechos corrigidos pelo usuário (o texto do modelo fica em original_text).
    corrected_segments: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_validator("segments", mode="before")
    @classmethod
    def _ensure_segments_list(
        cls, value: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        if value is None:
            return []
        return value

    @field_validator("speaker_aliases", mode="before")
    @classmethod
    def _ensure_aliases_dict(cls, value: Optional[Dict[str, str]]) -> Dict[str, str]:
        if value is None:
            return {}
        return value


class SegmentCorrectionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Texto corrigido do trecho.")


class SpeakerAliasesUpdateRequest(BaseModel):
    """Request schema for updating speaker aliases."""

    aliases: Dict[str, str] = Field(
        ...,
        description=(
            "Dictionary of speaker aliases "
            "(e.g., {'speaker_0': 'John Doe'})"
        ),
    )
