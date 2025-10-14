# src/media_management/domain/states/failed_state.py
from __future__ import annotations
from typing import TYPE_CHECKING

from .media_state import MediaState
from src.media_management.domain.enums import MediaStatus

if TYPE_CHECKING:
    from .processing_state import ProcessingState


class FailedState(MediaState):
    """Represents the state of a media that has failed processing."""

    def __init__(self, media, reason: str):
        super().__init__(media)
        self._media.error_message = reason

    def process(self):
        """Allows reprocessing a failed media item."""
        from .processing_state import ProcessingState
        self._media.error_message = None # Clear the error on retry
        self._media.state = ProcessingState(self._media)

    @property
    def status(self) -> MediaStatus:
        return MediaStatus.FAILED
