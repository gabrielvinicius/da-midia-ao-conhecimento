"""Extração de quadros de vídeo com o FFmpeg."""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Optional

import structlog

from src.media_processing.application.ports import VideoFrameExtractorPort

logger = structlog.get_logger(__name__)


class FFmpegFrameExtractor(VideoFrameExtractorPort):
    """Grava o vídeo uma vez em disco e extrai dele todos os quadros pedidos.

    Antes, o vídeo inteiro (até 500 MB) era regravado para cada quadro.
    """

    async def extract_frames(self, video_data: bytes, timestamps: list[float]) -> list[Optional[bytes]]:
        if not timestamps:
            return []
        with tempfile.TemporaryDirectory() as workdir:
            video_path = os.path.join(workdir, "video")
            with open(video_path, "wb") as video_file:
                video_file.write(video_data)
            return [await self._frame_at(video_path, ts, workdir, i) for i, ts in enumerate(timestamps)]

    @staticmethod
    async def _frame_at(video_path: str, timestamp: float, workdir: str, index: int) -> Optional[bytes]:
        image_path = os.path.join(workdir, f"frame-{index}.jpg")
        # -ss antes de -i: busca rápida pelo índice do contêiner.
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
            "-vframes", "1", "-q:v", "2", image_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0 or not os.path.exists(image_path):
            logger.warning("ffmpeg.extract_frame_failed", timestamp=timestamp, stderr=stderr.decode()[-300:])
            return None
        with open(image_path, "rb") as image:
            return image.read()


__all__ = ["FFmpegFrameExtractor"]
