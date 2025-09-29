# src/media_management/domain/states/media_state.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.media_management.domain.media import Media


class MediaState(ABC):
    """The Abstract Base Class for all media states (State Pattern)."""

    def __init__(self, media: Media):
        self._media = media

    def process(self):
        raise NotImplementedError("This action is not allowed in the current state.")

    def complete(self):
        raise NotImplementedError("This action is not allowed in the current state.")

    def fail(self, reason: str):
        raise NotImplementedError("This action is not allowed in the current state.")
