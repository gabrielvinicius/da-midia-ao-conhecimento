"""Read model accessors for transcriptions."""

from __future__ import annotations

from typing import Any, Optional


class TranscriptionQueries:
    """Provides read-only access patterns backed by the repository."""

    def __init__(self, transcription_repository: Any) -> None:
        self._repository = transcription_repository

    async def get_by_id(self, transcription_id: str) -> Optional[Any]:
        lookup = getattr(self._repository, "find_by_id", None) or getattr(self._repository, "get_by_id")
        return await lookup(transcription_id)

    async def get_by_media_id(self, media_id: str) -> Optional[Any]:
        lookup = getattr(self._repository, "find_by_media_id", None) or getattr(self._repository, "get_by_media_id")
        return await lookup(media_id)

    async def get_by_video_id(self, video_id: str) -> Optional[Any]:
        lookup = getattr(self._repository, "find_by_video_id", None)
        if lookup is None:
            lookup = getattr(self._repository, "get_by_media_id")
        return await lookup(video_id)

