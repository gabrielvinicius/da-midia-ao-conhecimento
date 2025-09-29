# src/media_management/domain/states/uploaded_state.py
from __future__ import annotations
from typing import TYPE_CHECKING

from .media_state import MediaState
from src.media_management.domain.media import MediaStatus

if TYPE_CHECKING:
    from .processing_state import ProcessingState
    from .failed_state import FailedState


class UploadedState(MediaState):
    """Represents the state of a media that has been successfully uploaded."""

    def process(self):
        """Transitions the media to the Processing state."""
        from .processing_state import ProcessingState
        self._media.state = ProcessingState(self._media)

    def fail(self, reason: str):
        """Transitions the media to the Failed state."""
        from .failed_state import FailedState
        self._media.state = FailedState(self._media, reason)

    @property
    def status(self) -> MediaStatus:
        return MediaStatus.UPLOADED
