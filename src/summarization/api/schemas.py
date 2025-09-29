# src/summarization/api/schemas.py
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class SummaryRequest(BaseModel):
    media_id: UUID
    provider: Optional[str] = "huggingface"


class SummaryResponse(BaseModel):
    id: str
    media_id: str
    status: str
    text: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True
