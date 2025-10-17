# src/video_processing/domain/interfaces.py
"""
Domain interfaces for video_processing module following DIP principle.
All high-level modules depend on these abstractions, not concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class VideoProcessor(ABC):
    """Interface for video processing services."""
    
    @abstractmethod
    async def process_video(self, video_data: bytes, target_format: str = "mp4") -> bytes:
        """Process video data to target format."""
        pass
    
    @abstractmethod
    async def extract_metadata(self, video_data: bytes) -> Dict[str, Any]:
        """Extract metadata from video data."""
        pass
    
    @abstractmethod
    async def validate_video(self, video_data: bytes) -> bool:
        """Validate if the video data is in a supported format."""
        pass


class VideoOrchestrator(ABC):
    """Interface for video processing orchestration services."""
    
    @abstractmethod
    async def process_video_upload(
        self,
        media_id: str,
        video_data: bytes,
        user_id: str,
        target_format: str = "mp4"
    ) -> Dict[str, Any]:
        """Orchestrate video processing workflow."""
        pass


class VideoNotificationService(ABC):
    """Interface for video processing notification services."""
    
    @abstractmethod
    async def notify_video_processing_started(self, user_id: str, media_id: str):
        """Notify user that video processing has started."""
        pass
    
    @abstractmethod
    async def notify_video_processing_completed(self, user_id: str, media_id: str, result: Dict[str, Any]):
        """Notify user that video processing has completed."""
        pass
    
    @abstractmethod
    async def notify_video_processing_failed(self, user_id: str, media_id: str, error: str):
        """Notify user that video processing has failed."""
        pass