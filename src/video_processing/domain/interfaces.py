# src/video_processing/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class IVideoAudioExtractor(ABC):
    """Interface for extracting audio from video files."""

    @abstractmethod
    async def extract_audio(self, video_data: bytes, filename: str, output_format: str = 'wav') -> Dict[str, Any]:
        """
        Extracts audio data from a given video file.
        Returns a dictionary containing audio_data (bytes), audio_format, and metadata.
        """
        pass


class IVideoThumbnailGenerator(ABC):
    """Interface for generating thumbnails from video files."""

    @abstractmethod
    async def generate_thumbnail(self, video_data: bytes, filename: str, size: str = 'medium', timestamp: float = 5.0) -> Dict[str, Any]:
        """
        Generates a thumbnail from a video file at a specific timestamp.
        Returns a dictionary containing thumbnail_data (bytes), thumbnail_format, size, dimensions, and metadata.
        """
        pass


class IVideoProcessingTaskScheduler(ABC):
    """Interface for scheduling video processing tasks."""

    @abstractmethod
    async def schedule_process_video_task(self, media_id: str, file_path: str) -> Any:
        """Schedules a video processing task."""
        pass
