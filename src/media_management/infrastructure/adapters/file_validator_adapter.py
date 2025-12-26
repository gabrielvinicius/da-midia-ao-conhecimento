from __future__ import annotations

from typing import List, Set

from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.storage.application.ports import FileReferenceValidatorPort


class MediaFileReferenceValidator(FileReferenceValidatorPort):
    """Validator that checks if files are referenced by Media entities."""

    def __init__(self, repository: MediaRepository) -> None:
        self._repository = repository

    async def validate_batch(self, provider: str, paths: List[str]) -> Set[str]:
        """Returns the subset of paths that are referenced in the media database."""
        # Note: MediaRepository.get_existing_paths implementation should handle
        # filtering by provider if the path doesn't implicitly contain it or
        # if the repository stores provider info. 
        # Current Media entity stores 'storage_provider'.
        # For simplicity, we assume paths are unique enough or checking existence is sufficient.
        # A more robust impl would check (path, provider) tuple.
        
        # To strictly filter by provider in DB query would require changes to 
        # get_existing_paths to accept provider. Assuming paths are globally unique for now
        # or that the collision risk is acceptable for cleanup.
        return await self._repository.get_existing_paths(paths)
