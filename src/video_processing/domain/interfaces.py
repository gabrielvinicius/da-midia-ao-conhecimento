# src/video_processing/domain/interfaces.py
"""
Domain interfaces for video_processing module following DIP principle.
All high-level modules depend on these abstractions, not concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class IVideoProcessor(ABC):
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


class IVideoOrchestrator(ABC):
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


class IVideoProcessor(ABC):
    """Enhanced interface for video processing operations."""
    
    @abstractmethod
    async def process_video(
        self, 
        video_data: bytes, 
        target_format: str = "mp4",
        options: Optional[Dict[str, Any]] = None
    ) -> bytes:
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


class IVideoValidator(ABC):
    """Interface for video validation operations."""
    
    @abstractmethod
    def validate_video_data(self, video_data: bytes) -> None:
        """Validate video data for processing."""
        pass
    
    @abstractmethod
    def validate_format_support(self, format_name: str) -> None:
        """Validate if format is supported for conversion."""
        pass
    
    @abstractmethod
    def validate_processing_options(self, options: Dict[str, Any]) -> None:
        """Validate processing options."""
        pass


class IVideoMetricsService(ABC):
    """Interface for video processing metrics operations."""
    
    @abstractmethod
    def record_processing_start(self, media_id: str) -> None:
        """Record start of video processing."""
        pass
    
    @abstractmethod
    def record_processing_success(
        self, 
        media_id: str, 
        input_size: int, 
        output_size: int,
        format_conversion: str,
        duration: float
    ) -> None:
        """Record successful video processing."""
        pass
    
    @abstractmethod
    def record_processing_failure(self, media_id: str, error: str) -> None:
        """Record failed video processing."""
        pass


class IVideoStateManager(ABC):
    """Interface for video processing state management."""
    
    @abstractmethod
    async def update_status(
        self, 
        media_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update video processing status."""
        pass
    
    @abstractmethod
    async def get_status(self, media_id: str) -> Optional[str]:
        """Get current video processing status."""
        pass


class IVideoNotificationService(ABC):
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


# Backward compatibility
VideoProcessor = IVideoProcessor


class IVideoProcessingFactory(ABC):
    """Factory interface for creating video processing services - DIP compliance."""
    
    @abstractmethod
    def create_processor_service(self) -> IVideoProcessor:
        """Create video processor service instance."""
        pass
    
    @abstractmethod
    def create_validator_service(self) -> IVideoValidator:
        """Create video validator service instance."""
        pass
    
    @abstractmethod
    def create_metrics_service(self) -> IVideoMetricsService:
        """Create video metrics service instance."""
        pass
    
    @abstractmethod
    def create_state_manager(self) -> IVideoStateManager:
        """Create video state manager instance."""
        pass
    
    @abstractmethod
    def create_notification_service(self) -> VideoNotificationService:
        """Create video notification service instance."""
        pass