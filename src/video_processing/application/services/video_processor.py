# src/video_processing/application/services/video_processor.py
"""
Video Processing Service - Single Responsibility Principle
Extracted from BaseVideoProcessingTemplate God Class (549 lines)
Handles core video processing operations
"""

import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.video_processing.domain.interfaces import VideoProcessingInput, VideoOperation, VideoFormat
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("video_processor")


class VideoProcessor:
    """
    Video processing with Single Responsibility:
    Execute video processing operations and manage temporary files
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.working_dir: Optional[str] = None
        self.temp_files: List[str] = []
        self.session_id: Optional[str] = None
        
    async def process_video(
        self, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main video processing entry point
        Returns processing result with output data
        """
        options = options or {}
        
        try:
            # Initialize processing session
            await self._initialize_session(input_data, options)
            
            # Save input video to temporary file
            input_file = await self._save_input_video(input_data)
            
            # Analyze video properties
            video_properties = await self._analyze_video_properties(input_file)
            
            # Execute the specific operation
            result = await self._execute_operation(input_data, input_file, options)
            
            # Add metadata to result
            result.update({
                "input_properties": video_properties,
                "session_id": self.session_id,
                "temp_files_created": len(self.temp_files)
            })
            
            logger.info(f"Video processing completed: {input_data.operation.value}")
            return result
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise
        finally:
            # Cleanup handled by context manager or explicit call
            pass
    
    async def _initialize_session(self, input_data: VideoProcessingInput, options: Dict[str, Any]):
        """Initialize processing session with working directory"""
        
        # Generate unique session ID
        self.session_id = f"video_{hash(input_data.video_data) % 100000}_{int(os.urandom(2).hex(), 16)}"
        
        # Create working directory
        self.working_dir = os.path.join(self.temp_dir, f"video_processing_{self.session_id}")
        os.makedirs(self.working_dir, exist_ok=True)
        
        logger.debug(f"Initialized video processing session: {self.session_id}")
        logger.debug(f"Working directory: {self.working_dir}")
    
    async def _save_input_video(self, input_data: VideoProcessingInput) -> str:
        """Save input video data to temporary file"""
        
        if not self.working_dir:
            raise ValueError("Session not initialized")
        
        # Determine file extension
        file_extension = input_data.input_format.value
        input_file = os.path.join(self.working_dir, f"input.{file_extension}")
        
        # Write video data to file
        with open(input_file, 'wb') as f:
            f.write(input_data.video_data)
        
        self.temp_files.append(input_file)
        
        logger.debug(f"Saved input video: {input_file} ({len(input_data.video_data)} bytes)")
        return input_file
    
    async def _analyze_video_properties(self, video_file: str) -> Dict[str, Any]:
        """Analyze video file properties"""
        
        try:
            file_size = os.path.getsize(video_file)
            
            # TODO: In production, use ffprobe for real analysis
            # This is a mock implementation
            properties = {
                "file_size": file_size,
                "duration": 60.0,  # Mock duration in seconds
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "bitrate": 5000000,  # bits per second
                "codec": "h264",
                "audio_codec": "aac",
                "has_audio": True,
                "has_video": True
            }
            
            logger.debug(f"Analyzed video properties: {properties}")
            return properties
            
        except Exception as e:
            logger.error(f"Error analyzing video properties: {e}")
            return {"error": str(e)}
    
    async def _execute_operation(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the specific video operation"""
        
        operation = input_data.operation
        
        if operation == VideoOperation.CONVERT_FORMAT:
            return await self._convert_format(input_data, input_file, options)
        
        elif operation == VideoOperation.COMPRESS:
            return await self._compress_video(input_data, input_file, options)
        
        elif operation == VideoOperation.RESIZE:
            return await self._resize_video(input_data, input_file, options)
        
        elif operation == VideoOperation.EXTRACT_AUDIO:
            return await self._extract_audio(input_data, input_file, options)
        
        elif operation == VideoOperation.EXTRACT_FRAMES:
            return await self._extract_frames(input_data, input_file, options)
        
        else:
            raise ValueError(f"Unsupported operation: {operation.value}")
    
    async def _convert_format(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert video to different format"""
        
        output_format = input_data.output_format.value
        output_file = os.path.join(self.working_dir, f"output.{output_format}")
        
        # TODO: Use ffmpeg for real conversion
        # Mock implementation: copy file with new extension
        shutil.copy2(input_file, output_file)
        self.temp_files.append(output_file)
        
        # Read output data
        with open(output_file, 'rb') as f:
            output_data = f.read()
        
        return {
            "type": "video",
            "operation": "format_conversion", 
            "output_format": output_format,
            "output_data": output_data,
            "output_size": len(output_data),
            "compression_ratio": len(input_data.video_data) / len(output_data)
        }
    
    async def _compress_video(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compress video with quality settings"""
        
        quality_level = getattr(input_data, 'quality_level', 80)
        output_file = os.path.join(self.working_dir, "compressed.mp4")
        
        # TODO: Use ffmpeg with quality settings
        # Mock implementation: reduce file size artificially
        with open(input_file, 'rb') as f:
            input_data_bytes = f.read()
        
        # Simulate compression (reduce by quality factor)
        compression_factor = quality_level / 100.0
        simulated_size = int(len(input_data_bytes) * compression_factor)
        compressed_data = input_data_bytes[:simulated_size]
        
        with open(output_file, 'wb') as f:
            f.write(compressed_data)
        
        self.temp_files.append(output_file)
        
        return {
            "type": "video",
            "operation": "compression",
            "output_data": compressed_data,
            "original_size": len(input_data.video_data),
            "compressed_size": len(compressed_data),
            "compression_ratio": len(compressed_data) / len(input_data.video_data),
            "quality_level": quality_level
        }
    
    async def _resize_video(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resize video to target dimensions"""
        
        target_width = input_data.target_width
        target_height = input_data.target_height
        output_file = os.path.join(self.working_dir, f"resized_{target_width}x{target_height}.mp4")
        
        # TODO: Use ffmpeg for real resizing
        # Mock implementation
        shutil.copy2(input_file, output_file)
        self.temp_files.append(output_file)
        
        with open(output_file, 'rb') as f:
            output_data = f.read()
        
        return {
            "type": "video",
            "operation": "resize",
            "output_data": output_data,
            "original_dimensions": {"width": 1920, "height": 1080},  # Mock
            "new_dimensions": {"width": target_width, "height": target_height},
            "scale_factor": (target_width * target_height) / (1920 * 1080)
        }
    
    async def _extract_audio(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract audio from video"""
        
        audio_format = getattr(input_data, 'output_audio_format', 'mp3')
        output_file = os.path.join(self.working_dir, f"audio.{audio_format}")
        
        # TODO: Use ffmpeg for real audio extraction
        # Mock implementation: create fake audio data
        mock_audio_data = b"mock_audio_data_" + os.urandom(1000)
        
        with open(output_file, 'wb') as f:
            f.write(mock_audio_data)
        
        self.temp_files.append(output_file)
        
        return {
            "type": "audio",
            "operation": "audio_extraction",
            "output_data": mock_audio_data,
            "audio_format": audio_format,
            "estimated_duration": 60.0,  # Mock duration
            "bitrate": 128000  # Mock bitrate
        }
    
    async def _extract_frames(
        self, 
        input_data: VideoProcessingInput, 
        input_file: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract frames from video"""
        
        max_frames = options.get('max_frames', 10)
        frame_rate = options.get('frame_rate', 1)  # frames per second
        
        frame_files = []
        frame_data_list = []
        
        # TODO: Use ffmpeg for real frame extraction
        # Mock implementation: create fake frame files
        for i in range(max_frames):
            frame_file = os.path.join(self.working_dir, f"frame_{i:04d}.jpg")
            mock_frame_data = f"mock_frame_data_{i}".encode() + os.urandom(500)
            
            with open(frame_file, 'wb') as f:
                f.write(mock_frame_data)
            
            frame_files.append(frame_file)
            frame_data_list.append(mock_frame_data)
            self.temp_files.append(frame_file)
        
        return {
            "type": "frames",
            "operation": "frame_extraction",
            "frame_files": frame_files,
            "frame_data": frame_data_list,
            "frame_count": len(frame_files),
            "extraction_rate": frame_rate,
            "format": "jpg"
        }
    
    async def cleanup(self):
        """Clean up temporary files and working directory"""
        
        if not self.working_dir:
            return
        
        try:
            # Remove all temp files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            # Remove working directory
            if os.path.exists(self.working_dir):
                shutil.rmtree(self.working_dir)
            
            logger.debug(f"Cleaned up session: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self.temp_files.clear()
            self.working_dir = None
            self.session_id = None
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "session_id": self.session_id,
            "working_dir": self.working_dir,
            "temp_files_count": len(self.temp_files),
            "temp_dir": self.temp_dir
        }
    
    # Context manager support
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# Default instance
video_processor = VideoProcessor()