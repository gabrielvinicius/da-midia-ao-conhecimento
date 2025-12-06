# src/media_processing/video_processing/infrastructure/video_thumbnail_generator.py
import asyncio
import io
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import structlog

try:  # pragma: no cover - optional dependency
    from PIL import Image, ImageDraw, ImageFont  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - degraded mode
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]

logger = structlog.get_logger(__name__)

class FFmpegVideoThumbnailGenerator:
    """Concrete implementation of IVideoThumbnailGenerator using FFmpeg and MoviePy/PIL as fallback."""

    def __init__(self):
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        self.thumbnail_sizes = {
            'small': (160, 120),
            'medium': (320, 240),
            'large': (640, 480)
        }

    async def generate_thumbnail(self, video_data: bytes, filename: str, size: str = 'medium', timestamp: float = 5.0) -> Dict[str, Any]:
        logger.info(
            "ffmpeg_video_thumbnail_generator.generating_thumbnail",
            filename=filename,
            size=size,
            timestamp=timestamp
        )
        try:
            # Check if file format is supported
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported video format: {file_ext}")

            # Generate thumbnail
            thumbnail_data = await self._generate_with_ffmpeg(
                video_data, filename, size, timestamp
            )

            # Get thumbnail metadata
            metadata = await self._get_thumbnail_metadata(thumbnail_data, size)

            return {
                'thumbnail_data': thumbnail_data,
                'thumbnail_format': 'jpeg',
                'size': size,
                'dimensions': self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium']),
                'timestamp': timestamp,
                'original_video_size': len(video_data),
                'thumbnail_size': len(thumbnail_data),
                'metadata': metadata,
                'success': True
            }

        except Exception as e:
            logger.error("Thumbnail generation failed", extra={"error": str(e), "filename": filename})
            raise

    async def _generate_with_ffmpeg(self, video_data: bytes, filename: str,
                                   size: str, timestamp: float) -> bytes:
        """Generate thumbnail using FFmpeg."""
        # Get dimensions for size
        width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])

        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as video_temp:
            video_temp.write(video_data)
            video_temp_path = video_temp.name

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as thumb_temp:
            thumb_temp_path = thumb_temp.name

        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', video_temp_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-vf', f'scale={width}:{height}',
                '-q:v', '2',
                thumb_temp_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg failed: {stderr.decode()}", stdout=stdout.decode(), stderr=stderr.decode())
                raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")

            with open(thumb_temp_path, 'rb') as f:
                thumbnail_data = f.read()

            return thumbnail_data

        finally:
            if os.path.exists(video_temp_path):
                os.unlink(video_temp_path)
            if os.path.exists(thumb_temp_path):
                os.unlink(thumb_temp_path)

    async def _get_thumbnail_metadata(self, thumbnail_data: bytes, size: str) -> Dict[str, Any]:
        """Get metadata from generated thumbnail."""
        width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])

        metadata = {
            'size_bytes': len(thumbnail_data),
            'format': 'jpeg',
            'width': width,
            'height': height,
            'aspect_ratio': width / height
        }

        if Image is not None:
            try:
                img = Image.open(io.BytesIO(thumbnail_data))
                metadata.update({
                    'mode': img.mode,
                    'actual_width': img.width,
                    'actual_height': img.height
                })
            except Exception as e:  # pragma: no cover - best effort
                logger.warning("Failed to extract detailed thumbnail metadata", error=str(e))
        else:  # pragma: no cover - optional dependency not installed
            logger.debug("Pillow not available; skipping thumbnail metadata enrichment")

        return metadata
