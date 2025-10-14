# src/media_management/domain/states/processing_state.py
from __future__ import annotations
from typing import TYPE_CHECKING

from .media_state import MediaState
from src.media_management.domain.enums import MediaStatus

if TYPE_CHECKING:
    from .completed_state import CompletedState
    from .failed_state import FailedState


class ProcessingState(MediaState):
    """Represents the state of a media that is being processed."""

    def complete(self):
        """Transitions the media to the Completed state."""
        from .completed_state import CompletedState
        self._media.state = CompletedState(self._media)

    def fail(self, reason: str):
        """Transitions the media to the Failed state."""
        from .failed_state import FailedState
        self._media.state = FailedState(self._media, reason)

    @property
    def status(self) -> MediaStatus:
        return MediaStatus.PROCESSING
