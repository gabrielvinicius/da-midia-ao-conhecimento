"""Value object representing a validated file path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class FilePath:
    """Immutable representation of a file path."""

    value: str

    def __post_init__(self) -> None:
        cleaned = str(self.value).strip()
        if not cleaned:
            raise ValueError("File path cannot be empty")
        normalised = Path(cleaned).as_posix()
        object.__setattr__(self, "value", normalised)

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> "FilePath":
        return cls(str(path))

    def to_path(self) -> Path:
        return Path(self.value)

    def get_extension(self) -> str:
        return self.to_path().suffix.lower()

    def get_filename(self) -> str:
        return self.to_path().name

    def __str__(self) -> str:
        return self.value
