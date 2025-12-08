from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import UUID


class AnalyzeTextCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media associated with the text.")
    document_id: UUID = Field(..., description="ID of the document to analyze.")
    text_content: str = Field(..., description="The actual text content to analyze.")
    user_id: Optional[UUID] = Field(None, description="ID of the user who owns the content.")
    transcription_id: Optional[UUID] = Field(None, description="ID of the transcription, if applicable.")
    language: Optional[str] = Field(None, description="Language of the text content.")
    
    class Config:
        frozen = True