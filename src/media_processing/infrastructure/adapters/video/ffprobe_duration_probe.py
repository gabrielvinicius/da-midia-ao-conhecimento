"""Duração de áudio e vídeo com o ffprobe (instalado junto com o ffmpeg)."""
from __future__ import annotations

import asyncio
import subprocess

import structlog

logger = structlog.get_logger(__name__)


class FfprobeDurationProbe:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self._timeout = timeout_seconds

    async def duration_seconds(self, file_path: str) -> float | None:
        return await asyncio.to_thread(self._probe, file_path)

    def _probe(self, file_path: str) -> float | None:
        try:
            completed = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            value = float(completed.stdout.strip())
            return value if value > 0 else None
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            # Sem duração, vale o prazo padrão; nunca impede a transcrição.
            logger.info("ffprobe.duration_unavailable", error=str(exc))
            return None
