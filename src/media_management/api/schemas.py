# src/media_management/api/schemas.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from src.media_management.domain.media import MediaType, MediaStatus


class MediaResponse(BaseModel):
    id: UUID
    user_id: UUID
    original_file_path: str
    media_type: MediaType
    status: MediaStatus
    created_at: datetime

    class Config:
        orm_mode = True
