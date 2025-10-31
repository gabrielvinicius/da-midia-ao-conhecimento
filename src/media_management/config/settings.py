"""Media management configuration objects."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class MediaSettings:
    """Default configuration for media management operations."""

    max_file_size_bytes: int = 100 * 1024 * 1024  # 100 MB
    min_file_size_bytes: int = 1 * 1024  # 1 KB
    allowed_video_extensions: Tuple[str, ...] = field(
        default_factory=lambda: ("mp4", "avi", "mov", "mkv", "webm", "flv")
    )
    allowed_audio_extensions: Tuple[str, ...] = field(
        default_factory=lambda: ("mp3", "wav", "flac", "aac", "ogg", "m4a")
    )
