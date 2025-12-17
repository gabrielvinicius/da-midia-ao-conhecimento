from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileSize:
    """Value object representing file size in bytes."""

    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise ValueError("File size must be non-negative")

    def __int__(self) -> int:
        return self.bytes

    def __str__(self) -> str:
        return f"{self.bytes} bytes"
