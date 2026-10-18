"""Quais quadros de um vídeo descrever (regra pura, sem modelos)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, Optional

# Semelhança (palavras em comum) a partir da qual duas descrições seguidas são
# a mesma cena (padrão de PROCESSING_SAME_SCENE_SIMILARITY). Num vídeo de uma
# pessoa falando para a câmera, 5 das 8 descrições eram variações de "um homem
# de camiseta preta fala ao microfone"; repetidas, só ocupavam o prompt e o
# apêndice.
SAME_SCENE_SIMILARITY = 0.55

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


def is_same_scene(previous: Optional[str], current: str, threshold: float = SAME_SCENE_SIMILARITY) -> bool:
    """Se a descrição repete a cena da anterior (semelhança de Jaccard das palavras)."""
    if not previous:
        return False
    a, b = _words(previous), _words(current)
    return bool(a and b) and len(a & b) / len(a | b) >= threshold


@dataclass(frozen=True)
class FrameSampling:
    """Quantos quadros descrever e quando duas descrições são a mesma cena;
    vem das configurações PROCESSING_FRAME_* e PROCESSING_SAME_SCENE_SIMILARITY."""

    seconds_per_frame: float = 180.0
    min_frames: int = 3
    max_frames: int = 8
    same_scene_similarity: float = SAME_SCENE_SIMILARITY

    def __post_init__(self) -> None:
        if self.seconds_per_frame <= 0 or not 0 <= self.min_frames <= self.max_frames:
            raise ValueError("PROCESSING_FRAME_*: intervalo positivo e mínimo de quadros até o máximo")

    def timestamps(self, duration: float) -> List[float]:
        return frame_timestamps(duration, self.seconds_per_frame, self.min_frames, self.max_frames)

    def is_same_scene(self, previous: Optional[str], current: str) -> bool:
        return is_same_scene(previous, current, self.same_scene_similarity)


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))
