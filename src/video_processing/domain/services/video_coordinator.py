# src/video_processing/domain/services/video_coordinator.py
"""
Domain service for coordinating video processing operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from src.video_processing.domain.interfaces import (
    VideoProcessor,
    VideoValidator,
    VideoOperationLogger,
    VideoMetrics,
    VideoNotificationService
)


class VideoProcessingError(Exception):
    """Domain exception for video processing errors."""
    pass


class VideoCoordinator:
    """
    Domain service that coordinates video processing operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        processor: VideoProcessor,
        validator: VideoValidator,
        logger: VideoOperationLogger,
        metrics: VideoMetrics,
        notification_service: VideoNotificationService
    ):
        self._processor = processor
        self._validator = validator
        self._logger = logger
        self._metrics = metrics
        self._notification_service = notification_service
    
    async def process_video_file(
        self, 
        media_id: str,
        video_data: bytes,
        operation: str,
        user_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process video with complete workflow coordination."""
        start_time = datetime.utcnow()
        success = False
        error = None
        file_size = len(video_data)
        video_duration = 0.0
        
        try:
            # Notify processing started
            await self._notification_service.notify_started(media_id, user_id, operation)
            
            # Validate video
            if not await self._processor.validate_video(video_data):
                raise VideoProcessingError("Invalid video data")
            
            # Extract video information
            video_info = await self._processor.extract_video_info(video_data)
            video_duration = video_info.get("duration", 0.0)
            
            # Perform requested operation
            result = await self._perform_operation(
                operation, video_data, options or {}
            )
            
            # Combine results
            final_result = {
                "operation": operation,
                "video_info": video_info,
                "result": result,
                "metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "file_size": file_size,
                    "duration": video_duration
                }
            }
            
            # Notify completion
            await self._notification_service.notify_completed(media_id, user_id, final_result)
            
            success = True
            return final_result
            
        except Exception as e:
            error = e
            success = False
            
            # Notify failure
            await self._notification_service.notify_failed(media_id, user_id, str(e))
            
            raise VideoProcessingError(
                f"Failed to process video for media {media_id}: {e}"
            ) from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation=operation,
                media_id=media_id,
                format_type="video",
                success=success,
                duration=duration,
                file_size=file_size,
                video_duration=video_duration,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation=operation,
                format_type="video",
                duration=duration,
                success=success,
                file_size=file_size,
                video_duration=video_duration
            )
    
    async def _perform_operation(
        self, 
        operation: str, 
        video_data: bytes, 
        options: Dict[str, Any]
    ) -> Any:
        """Perform the specific video operation."""
        if operation == "extract_audio":
            return await self._processor.extract_audio_from_video(video_data)
        
        elif operation == "resize":
            width = options.get("width", 1280)
            height = options.get("height", 720)
            return await self._processor.resize_video(video_data, width, height)
        
        elif operation == "compress":
            quality = options.get("quality", "medium")
            return await self._processor.compress_video(video_data, quality)
        
        elif operation == "info":
            return await self._processor.extract_video_info(video_data)
        
        else:
            raise VideoProcessingError(f"Unknown operation: {operation}")
    
    async def extract_audio_only(
        self, 
        media_id: str,
        video_data: bytes,
        user_id: str
    ) -> bytes:
        """Extract audio from video - specialized method."""
        start_time = datetime.utcnow()
        success = False
        error = None
        
        try:
            # Notify processing started
            await self._notification_service.notify_started(media_id, user_id, "extract_audio")
            
            # Validate video
            if not await self._processor.validate_video(video_data):
                raise VideoProcessingError("Invalid video data for audio extraction")
            
            # Extract audio
            audio_data = await self._processor.extract_audio_from_video(video_data)
            
            success = True
            return audio_data
            
        except Exception as e:
            error = e
            success = False
            
            # Notify failure
            await self._notification_service.notify_failed(media_id, user_id, str(e))
            
            raise VideoProcessingError(
                f"Failed to extract audio from video {media_id}: {e}"
            ) from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="extract_audio",
                media_id=media_id,
                format_type="video",
                success=success,
                duration=duration,
                file_size=len(video_data),
                error=error
            )
    
    async def get_video_information(
        self, 
        media_id: str,
        video_data: bytes
    ) -> Dict[str, Any]:
        """Get video information with error handling."""
        try:
            # Validate video
            if not await self._processor.validate_video(video_data):
                raise VideoProcessingError("Invalid video data")
            
            # Extract information
            info = await self._processor.extract_video_info(video_data)
            
            # Add validation results
            quality_score = await self._validator.get_quality_score(video_data)
            info["quality_score"] = quality_score
            
            return info
            
        except Exception as e:
            await self._logger.log_operation(
                operation="get_info",
                media_id=media_id,
                format_type="video",
                success=False,
                duration=0.0,
                file_size=len(video_data),
                error=e
            )
            raise VideoProcessingError(f"Failed to get video info: {e}") from e