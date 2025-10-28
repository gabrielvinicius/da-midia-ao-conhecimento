"""File validation collaborators for media command handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.shared.exceptions.domain_exceptions import ValidationError


class MediaFileValidator(Protocol):
    """Validates file payloads for media commands."""

    def validate(self, file_data: bytes, filename: str) -> None:
        """Validate file contents and metadata."""


@dataclass
class FileSizeMediaFileValidator(MediaFileValidator):
    """Ensures files respect configured size constraints."""

    min_size_bytes: int
    max_size_bytes: int

    def validate(self, file_data: bytes, filename: str) -> None:
        if not file_data:
            raise ValidationError("file", filename, "File content is empty")

        file_size = len(file_data)

        if file_size > self.max_size_bytes:
            raise ValidationError("file", filename, "File size exceeds maximum limit")

        if file_size < self.min_size_bytes:
            raise ValidationError("file", filename, "File size is too small")
