from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# --- Commands ---

class RequestTranscriptionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media to transcribe.")
    file_path: str = Field(..., description="Path to the media file in storage.")
    storage_provider: str = Field(
        ...,
        description="Provider where the media file is stored.",
    )
    transcription_provider: str = Field(
        ...,
        description="Provider to use for transcription.",
    )
    language: str = Field(..., description="Language of the media content.")
    file_size_bytes: int = Field(
        0,
        ge=0,
        description="Size of the media file in bytes.",
    )
    summarization_provider: Optional[str] = Field(
        None,
        description="Provider to use for summarization.",
    )
    sentiment_provider: Optional[str] = Field(
        None,
        description="Provider to use for sentiment analysis.",
    )
    topic_modeling_provider: Optional[str] = Field(
        None,
        description="Provider to use for topic modeling.",
    )
    user_id: Optional[UUID] = Field(
        None,
        description="Owner of the media (for audit).",
    )
    filename: Optional[str] = Field(
        None,
        description="Original filename for context/audit.",
    )
    triggered_by: Optional[str] = Field(
        None,
        description="Who triggered the processing (user/admin/system).",
    )
    actor_id: Optional[str] = Field(
        None,
        description="Actor identifier that triggered the event.",
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation id propagated from MediaUploaded.",
    )



class RequestTextExtractionCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media to extract text from.")
    file_path: str = Field(..., description="Path to the file in storage.")
    storage_provider: str = Field(
        ..., description="Provider where the file is stored."
    )
    user_id: Optional[UUID] = Field(
        None, description="Owner of the media (for audit)."
    )
    filename: Optional[str] = Field(
        None, description="Original filename for context/audit."
    )
    triggered_by: Optional[str] = Field(
        None, description="Who triggered the processing (user/admin/system)."
    )
    actor_id: Optional[str] = Field(
        None, description="Actor identifier that triggered the event."
    )
    correlation_id: Optional[str] = Field(
        None, description="Correlation id propagated from MediaUploaded."
    )


class SetSpeakerAliasesCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    transcription_id: UUID = Field(
        ...,
        description="ID of the transcription to update.",
    )
    aliases: Dict[str, str] = Field(
        ...,
        description="Mapping of speaker IDs to their aliases.",
    )


# --- Queries ---

class GetTranscriptionByMediaIdQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    media_id: UUID = Field(..., description="ID of the media to get transcription for.")


class GetTranscriptionByIdQuery(BaseModel):
    model_config = ConfigDict(frozen=True)
    transcription_id: UUID = Field(
        ...,
        description="ID of the transcription to retrieve.",
    )
