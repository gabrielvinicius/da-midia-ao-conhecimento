"""Media management configuration objects."""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class MediaSettings:
    """Default configuration for media management operations."""

    max_file_size_bytes: int = 500 * 1024 * 1024  # 500 MB (aligned with backend handler)
    min_file_size_bytes: int = 1  # permite qualquer conteúdo não vazio
    allowed_video_extensions: Tuple[str, ...] = field(
        default_factory=lambda: ("mp4", "avi", "mov", "mkv", "webm", "flv")
    )
    allowed_audio_extensions: Tuple[str, ...] = field(
        default_factory=lambda: ("mp3", "wav", "flac", "aac", "ogg", "m4a")
    )
    allowed_text_extensions: Tuple[str, ...] = field(
        default_factory=lambda: ("txt", "pdf", "doc", "docx")
    )
