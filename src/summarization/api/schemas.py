# src/summarization/api/schemas.py
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

# Import the status enum from the domain layer for consistency
from src.summarization.domain.summary import SummaryStatus


class SummaryRequest(BaseModel):
    """Schema for requesting a new summary for a media item."""
    media_id: UUID = Field(..., description="The ID of the media item to be summarized.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    provider: Optional[str] = Field("huggingface", description="The summarization provider to use.", example="huggingface")


class SummaryResponse(BaseModel):
    """Schema for returning summary information."""
    id: UUID = Field(..., description="The unique identifier for the summary record.", example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    media_id: UUID = Field(..., description="The ID of the media item this summary belongs to.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    status: SummaryStatus = Field(..., description="The current status of the summarization process.", example="COMPLETED")
    provider: Optional[str] = Field(None, description="The service provider used for this summarization.", example="huggingface")
    text: Optional[str] = Field(None, description="The full summarized text.", example="This is the final summary of the content.")
    created_at: datetime = Field(..., description="The timestamp when the summarization process was initiated.")
    processed_at: Optional[datetime] = Field(None, description="The timestamp when the summarization process was completed or failed.")
    error_message: Optional[str] = Field(None, description="Any error message if the summarization failed.")

    class Config:
        from_attributes = True
