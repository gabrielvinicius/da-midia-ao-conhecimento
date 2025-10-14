# src/media_management/domain/states/completed_state.py
from __future__ import annotations
from typing import TYPE_CHECKING

from .media_state import MediaState
from src.media_management.domain.enums import MediaStatus


class CompletedState(MediaState):
    """Represents the state of a media that has been successfully processed."""

    # No transitions are allowed from the completed state.

    @property
    def status(self) -> MediaStatus:
        return MediaStatus.COMPLETED
