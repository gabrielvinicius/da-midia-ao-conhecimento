"""Adapter for extracting frames from video using FFmpeg."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
import structlog

from src.media_processing.application.ports import VideoFrameExtractorPort

logger = structlog.get_logger(__name__)

class FFmpegFrameExtractor(VideoFrameExtractorPort):
    """Uses FFmpeg to extract a single frame at a specific timestamp."""

    async def extract_frame(self, video_data: bytes, timestamp: float) -> bytes:
        logger.debug("ffmpeg.extract_frame", timestamp=timestamp)
        
        # Create temporary video file from bytes
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_temp:
            video_temp.write(video_data)
            video_temp_path = video_temp.name

        # Create temporary output image path
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as img_temp:
            img_temp_path = img_temp.name

        try:
            # -ss before -i is faster (seeking)
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(timestamp),
                '-i', video_temp_path,
                '-vframes', '1',
                '-q:v', '2',
                img_temp_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error("ffmpeg.extract_frame_failed", stderr=stderr.decode())
                raise RuntimeError("Failed to extract frame via FFmpeg")

            with open(img_temp_path, 'rb') as f:
                return f.read()

        finally:
            if os.path.exists(video_temp_path):
                os.unlink(video_temp_path)
            if os.path.exists(img_temp_path):
                os.unlink(img_temp_path)

__all__ = ["FFmpegFrameExtractor"]
