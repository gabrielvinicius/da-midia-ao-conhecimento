# src/media_management/domain/media.py
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Enum as SqlEnum, DateTime, ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.database import Base
from .states.media_state import MediaState
from .states.uploaded_state import UploadedState
from .states.processing_state import ProcessingState
from .states.completed_state import CompletedState
from .states.failed_state import FailedState

class MediaType(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    TEXT = "TEXT"

class MediaStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_file_path = Column(String, nullable=False)
    media_type = Column(SqlEnum(MediaType), nullable=False)
    status = Column(SqlEnum(MediaStatus), default=MediaStatus.UPLOADED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    error_message = Column(String, nullable=True)

    # New fields to store user's provider choice
    transcription_provider = Column(String, nullable=True)
    summarization_provider = Column(String, nullable=True)

    _state: MediaState = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reconstitute_state()

    @property
    def state(self) -> MediaState:
        return self._state

    @state.setter
    def state(self, new_state: MediaState):
        self._state = new_state
        self.status = new_state.status

    def process(self):
        self.state.process()

    def complete(self):
        self.state.complete()

    def fail(self, reason: str):
        self.state.fail(reason)
    
    def reset_status(self):
        """Resets the media status to PENDING for reprocessing."""
        self.status = MediaStatus.UPLOADED
        self.error_message = None
        self._reconstitute_state()

    def _reconstitute_state(self):
        """Internal method to set the state object based on the status enum."""
        status = self.status
        if status == MediaStatus.UPLOADED:
            self._state = UploadedState(self)
        elif status == MediaStatus.PROCESSING:
            self._state = ProcessingState(self)
        elif status == MediaStatus.COMPLETED:
            self._state = CompletedState(self)
        elif status == MediaStatus.FAILED:
            self._state = FailedState(self, self.error_message or "Unknown error")
        else:
            self._state = UploadedState(self) # Default fallback


@event.listens_for(Media, 'load')
def _reconstitute_media_state(media: Media, _):
    """When a Media object is loaded from the DB, reconstitute its state object."""
    media._reconstitute_state()
