from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, slots=True)
class FilePath:
    """Value object representing a normalized storage path."""

    path: PurePosixPath

    @staticmethod
    def from_path(raw: str) -> "FilePath":
        if not raw or raw.strip() == "":
            raise ValueError("File path cannot be empty")
        # Normalize to POSIX style for storage consistency
        normalized = PurePosixPath(raw)
        return FilePath(path=normalized)

    @property
    def value(self) -> str:
        """Return path as POSIX string for adapters that expect `.value`."""
        return str(self.path)

    def to_path(self) -> Path:
        """Return a concrete Path for local filesystem-based adapters."""
        return Path(self.path)

    def __str__(self) -> str:
        return str(self.path)
