"""Quais quadros de um vídeo descrever (regra pura, sem modelos)."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import List, Optional

# Formatos de vídeo aceitos no envio; áudios e documentos não têm quadros.
VIDEO_EXTENSIONS = frozenset({".mp4", ".webm", ".mov", ".avi", ".mkv", ".flv"})


def is_video_file(path: Optional[str]) -> bool:
    return bool(path) and PurePosixPath(str(path)).suffix.lower() in VIDEO_EXTENSIONS


def frame_timestamps(
    duration: float,
    seconds_per_frame: float = 180.0,
    min_frames: int = 3,
    max_frames: int = 8,
) -> List[float]:
    """Instantes (em segundos) dos quadros: um a cada ~3 min, entre 3 e 8,
    no meio de cada intervalo (evita abertura e encerramento)."""
    if not duration or duration <= 0:
        return []
    count = max(min_frames, min(max_frames, round(duration / seconds_per_frame)))
    return [duration * (i + 0.5) / count for i in range(count)]


def format_timestamp(seconds: float) -> str:
    seconds = int(max(0, seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
