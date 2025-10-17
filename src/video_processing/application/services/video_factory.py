# src/video_processing/application/services/video_factory.py
"""
Video Factory Service following SRP principle.
Responsible only for creating video processing entities.
"""
from typing import Dict, Any
from uuid import UUID


class VideoFactory:
    """Factory for creating video processing entities."""
    
    def create_processing_result(
        self,
        media_id: UUID,
        original_format: str,
        target_format: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a video processing result."""
        return {
            "media_id": str(media_id),
            "original_format": original_format,
            "target_format": target_format,
            "metadata": metadata or {},
            "status": "completed",
            "processed_at": None  # Will be set by the processor
        }
    
    def create_error_result(
        self,
        media_id: UUID,
        error_message: str,
        error_code: str = "PROCESSING_ERROR"
    ) -> Dict[str, Any]:
        """Create an error result for video processing."""
        return {
            "media_id": str(media_id),
            "status": "failed",
            "error": {
                "code": error_code,
                "message": error_message
            },
            "processed_at": None
        }