"""Esquemas da API de mídias."""
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.media_management.domain.entities.media import Media, MediaStatus, MediaType
from src.shared.api.schemas import PaginatedResponse


class MediaResponse(BaseModel):
    """DTO for Media responses.
    Decoupled from Domain Entities and Internal Database columns.
    """

    id: UUID = Field(..., description="The unique identifier for the media item.")
    user_id: UUID = Field(..., description="Dono da mídia (a interface mostra as ações do dono).")
    filename: Optional[str] = Field(None, description="Original filename.")
    content_type: Optional[str] = Field(None, description="MIME type of the file.")
    size: Optional[int] = Field(None, description="File size in bytes.")
    media_type: MediaType = Field(..., description="The type of the media file.")
    status: MediaStatus = Field(..., description="The current processing status.")
    created_at: datetime = Field(
        ...,
        description="The timestamp when the media was uploaded.",
    )

    # Optional metadata
    error_message: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None

    # Providers
    storage_provider: Optional[str] = None
    transcription_provider: Optional[str] = None

    @classmethod
    def from_domain(cls, media: Media) -> "MediaResponse":
        return cls(
            id=media.id,
            user_id=media.user_id,
            filename=media.filename,
            content_type=media.mime_type,
            size=media.file_size,
            media_type=media.media_type,
            created_at=media.created_at,
            status=media.status,
            error_message=media.error_message,
            language=media.language,
            duration=media.duration,
            storage_provider=media.storage_provider,
            transcription_provider=media.transcription_provider,
        )

    model_config = ConfigDict(from_attributes=True)


def media_page(page_data, page: int, limit: int) -> PaginatedResponse[MediaResponse]:
    """Página de mídias no formato comum das listas."""
    return PaginatedResponse[MediaResponse](
        items=[MediaResponse.from_domain(media) for media in page_data.items],
        total=page_data.total,
        page=page_data.page or page,
        limit=page_data.limit or limit,
        pages=page_data.pages if page_data.pages is not None else PaginatedResponse.pages_for(page_data.total, limit),
    )


class MediaStatisticsResponse(BaseModel):
    """Mídias por estado e por tipo (chaves em minúsculas, como nos enums)."""

    total: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
