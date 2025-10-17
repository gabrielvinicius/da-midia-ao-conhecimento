"""
Video Processing Template Methods using Template Method Pattern
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import os

from src.shared.patterns.template_method import TemplateMethodBase, ProcessingResult, TemplateMethodFactory


class VideoOperation(str, Enum):
    """Video processing operations"""
    TRANSCODE = "transcode"
    EXTRACT_AUDIO = "extract_audio"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    COMPRESS = "compress"
    CONVERT_FORMAT = "convert_format"
    EXTRACT_FRAMES = "extract_frames"


class VideoFormat(str, Enum):
    """Supported video formats"""
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"


class AudioFormat(str, Enum):
    """Supported audio formats"""
    MP3 = "mp3"
    WAV = "wav"
    AAC = "aac"
    FLAC = "flac"
    OGG = "ogg"


@dataclass
class VideoProcessingInput:
    """Input data for video processing template methods"""
    video_data: bytes
    operation: VideoOperation
    input_format: VideoFormat
    output_format: Optional[VideoFormat] = None
    output_audio_format: Optional[AudioFormat] = None
    quality: str = "medium"  # low, medium, high, custom
    custom_params: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_params is None:
            self.custom_params = {}
        if self.metadata is None:
            self.metadata = {}


class BaseVideoProcessingTemplate(TemplateMethodBase[VideoProcessingInput, Dict[str, Any]]):
    """
    Base template for all video processing algorithms.
    Defines the common structure for video processing operations.
    """
    
    def __init__(self, provider_name: str, tool_version: str = None):
        super().__init__(f"{provider_name}VideoProcessingTemplate")
        self.provider_name = provider_name
        self.tool_version = tool_version or "default"
        self.temp_files = []
        self.processed_result = None
    
    async def _initialize(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Any:
        """Initialize video processing session"""
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("tool_version", self.tool_version)
        self.processing_result.add_metadata("operation", input_data.operation.value)
        self.processing_result.add_metadata("input_format", input_data.input_format.value)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        # Create temporary working directory
        temp_dir = options.get("temp_dir", "/tmp")
        session_id = f"{self.provider_name}_{hash(input_data.video_data) % 10000}"
        self.working_dir = f"{temp_dir}/video_processing_{session_id}"
        
        return {
            "provider": self.provider_name,
            "tool_version": self.tool_version,
            "session_id": session_id,
            "working_dir": self.working_dir
        }
    
    async def _validate(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> bool:
        """Validate video input"""
        
        # Check video data
        if not input_data.video_data or len(input_data.video_data) == 0:
            self.processing_result.add_error("Video data is empty")
            return False
        
        # Check video size limits
        max_size = options.get("max_video_size_mb", 500) * 1024 * 1024
        if len(input_data.video_data) > max_size:
            self.processing_result.add_error(
                f"Video size {len(input_data.video_data)} exceeds limit {max_size}"
            )
            return False
        
        # Check format support
        supported_input_formats = await self._get_supported_input_formats()
        if input_data.input_format not in supported_input_formats:
            self.processing_result.add_error(
                f"Input format '{input_data.input_format.value}' not supported. "
                f"Supported: {', '.join([f.value for f in supported_input_formats])}"
            )
            return False
        
        # Validate operation-specific requirements
        if not await self._validate_operation_specific(input_data, options):
            return False
        
        # Provider-specific validation
        return await self._validate_provider_specific(input_data, options)
    
    async def _preprocess(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Any:
        """Preprocess video data"""
        
        # Create working directory
        await self._create_working_directory()
        
        # Save input video to temporary file
        input_file = await self._save_input_video(input_data)
        
        # Analyze video properties
        video_info = await self._analyze_video_properties(input_file, options)
        
        # Validate video integrity
        is_valid = await self._validate_video_integrity(input_file, options)
        if not is_valid:
            self.processing_result.add_error("Video file is corrupted or invalid")
            return None
        
        # Apply preprocessing based on operation
        preprocessed_file = await self._preprocess_for_operation(
            input_file,
            input_data.operation,
            options
        )
        
        self.processing_result.add_metadata("preprocessing", {
            "input_file": input_file,
            "preprocessed_file": preprocessed_file,
            "video_info": video_info,
            "integrity_check": is_valid
        })
        
        return preprocessed_file
    
    async def _process(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Dict[str, Any]:
        """Core video processing"""
        
        # Get preprocessed input file
        input_file = self.processing_result.stage_results.get("preprocess")
        if not input_file:
            raise ValueError("No preprocessed input file available")
        
        # Process based on operation type
        if input_data.operation == VideoOperation.TRANSCODE:
            result = await self._perform_transcoding(input_file, input_data, options)
        elif input_data.operation == VideoOperation.EXTRACT_AUDIO:
            result = await self._perform_audio_extraction(input_file, input_data, options)
        elif input_data.operation == VideoOperation.GENERATE_THUMBNAIL:
            result = await self._perform_thumbnail_generation(input_file, input_data, options)
        elif input_data.operation == VideoOperation.COMPRESS:
            result = await self._perform_compression(input_file, input_data, options)
        elif input_data.operation == VideoOperation.CONVERT_FORMAT:
            result = await self._perform_format_conversion(input_file, input_data, options)
        elif input_data.operation == VideoOperation.EXTRACT_FRAMES:
            result = await self._perform_frame_extraction(input_file, input_data, options)
        else:
            raise ValueError(f"Unsupported operation: {input_data.operation}")
        
        self.processed_result = result
        return result
    
    async def _postprocess(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Any:
        """Post-process video processing results"""
        
        if not self.processed_result:
            return None
        
        # Validate output quality
        quality_metrics = await self._assess_output_quality(
            self.processed_result,
            input_data,
            options
        )
        
        # Optimize output if needed
        optimized_result = await self._optimize_output(
            self.processed_result,
            input_data,
            options
        )
        
        # Generate metadata
        output_metadata = await self._generate_output_metadata(
            optimized_result,
            input_data,
            options
        )
        
        # Update result with post-processed data
        if optimized_result != self.processed_result:
            self.processed_result = optimized_result
        
        self.processed_result["quality_metrics"] = quality_metrics
        self.processed_result["metadata"] = output_metadata
        
        self.processing_result.add_metadata("postprocessing", {
            "quality_assessed": bool(quality_metrics),
            "output_optimized": optimized_result != self.processed_result,
            "metadata_generated": bool(output_metadata)
        })
        
        return self.processed_result
    
    async def _finalize(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize video processing and cleanup"""
        
        if not self.processed_result:
            raise ValueError("No processing result available")
        
        # Read output data from files
        final_result = await self._read_output_data(self.processed_result)
        
        # Add final metadata
        final_result["processing_metadata"] = {
            "provider": self.provider_name,
            "tool_version": self.tool_version,
            "processing_time": self.processing_result.processing_time,
            "operation": input_data.operation.value,
            "input_size": len(input_data.video_data),
            "output_size": len(final_result.get("data", b""))
        }
        
        # Cleanup temporary files
        await self._cleanup_temp_files()
        
        # Cleanup provider resources
        await self._cleanup_provider()
        
        # Set final result
        self.processing_result.result = final_result
        
        return final_result
    
    def _should_preprocess(self) -> bool:
        """Enable preprocessing by default"""
        return True
    
    def _should_postprocess(self) -> bool:
        """Enable postprocessing by default"""
        return True
    
    # Abstract methods for provider-specific implementation
    
    async def _initialize_provider(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources. Override in subclasses."""
        pass
    
    async def _get_supported_input_formats(self) -> List[VideoFormat]:
        """Get supported input formats. Override in subclasses."""
        return list(VideoFormat)
    
    async def _validate_provider_specific(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> bool:
        """Provider-specific validation. Override in subclasses."""
        return True
    
    async def _perform_transcoding(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform video transcoding. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _perform_transcoding")
    
    async def _cleanup_provider(self) -> None:
        """Cleanup provider resources. Override in subclasses."""
        pass
    
    # Helper methods with default implementations
    
    async def _validate_operation_specific(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> bool:
        """Validate operation-specific requirements"""
        
        if input_data.operation == VideoOperation.CONVERT_FORMAT:
            if not input_data.output_format:
                self.processing_result.add_error("Output format required for format conversion")
                return False
        
        elif input_data.operation == VideoOperation.EXTRACT_AUDIO:
            if not input_data.output_audio_format:
                self.processing_result.add_error("Output audio format required for audio extraction")
                return False
        
        return True
    
    async def _create_working_directory(self) -> None:
        """Create working directory for temporary files"""
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir, exist_ok=True)
    
    async def _save_input_video(self, input_data: VideoProcessingInput) -> str:
        """Save input video to temporary file"""
        input_file = f"{self.working_dir}/input.{input_data.input_format.value}"
        
        with open(input_file, 'wb') as f:
            f.write(input_data.video_data)
        
        self.temp_files.append(input_file)
        return input_file
    
    async def _analyze_video_properties(self, video_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze video file properties"""
        
        # In practice, use ffprobe or similar tool
        # This is a mock implementation
        
        file_size = os.path.getsize(video_file)
        
        return {
            "file_size": file_size,
            "duration": 60.0,  # Mock duration in seconds
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "bitrate": 5000000,  # bits per second
            "codec": "h264",
            "audio_codec": "aac"
        }
    
    async def _validate_video_integrity(self, video_file: str, options: Dict[str, Any]) -> bool:
        """Validate video file integrity"""
        
        # Basic check: file exists and has content
        if not os.path.exists(video_file):
            return False
        
        if os.path.getsize(video_file) == 0:
            return False
        
        # In practice, use ffmpeg to validate
        return True
    
    async def _preprocess_for_operation(
        self, 
        input_file: str, 
        operation: VideoOperation, 
        options: Dict[str, Any]
    ) -> str:
        """Apply preprocessing specific to operation"""
        
        # For most operations, no specific preprocessing needed
        return input_file
    
    async def _perform_audio_extraction(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract audio from video"""
        
        output_file = f"{self.working_dir}/audio.{input_data.output_audio_format.value}"
        
        # Mock audio extraction
        # In practice, use ffmpeg: ffmpeg -i input.mp4 -vn -acodec copy output.aac
        
        # Create mock audio file
        with open(output_file, 'wb') as f:
            f.write(b'mock_audio_data')
        
        self.temp_files.append(output_file)
        
        return {
            "type": "audio",
            "file": output_file,
            "format": input_data.output_audio_format.value,
            "duration": 60.0,  # Mock duration
            "sample_rate": 44100,
            "channels": 2
        }
    
    async def _perform_thumbnail_generation(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate thumbnail from video"""
        
        timestamp = options.get("thumbnail_timestamp", 5.0)  # 5 seconds by default
        output_file = f"{self.working_dir}/thumbnail.jpg"
        
        # Mock thumbnail generation
        # In practice, use ffmpeg: ffmpeg -i input.mp4 -ss 00:00:05 -vframes 1 thumbnail.jpg
        
        # Create mock thumbnail file
        with open(output_file, 'wb') as f:
            f.write(b'mock_thumbnail_data')
        
        self.temp_files.append(output_file)
        
        return {
            "type": "image",
            "file": output_file,
            "format": "jpg",
            "timestamp": timestamp,
            "width": 320,
            "height": 180
        }
    
    async def _perform_compression(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compress video"""
        
        output_file = f"{self.working_dir}/compressed.{input_data.input_format.value}"
        
        # Mock compression
        # In practice, use ffmpeg with compression settings
        
        # Create mock compressed file (smaller than input)
        with open(input_file, 'rb') as infile:
            data = infile.read()
        
        # Mock compression by taking half the data
        compressed_data = data[:len(data)//2]
        
        with open(output_file, 'wb') as f:
            f.write(compressed_data)
        
        self.temp_files.append(output_file)
        
        return {
            "type": "video",
            "file": output_file,
            "format": input_data.input_format.value,
            "compression_ratio": 0.5,
            "quality": input_data.quality
        }
    
    async def _perform_format_conversion(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert video format"""
        
        output_file = f"{self.working_dir}/converted.{input_data.output_format.value}"
        
        # Mock format conversion
        # In practice, use ffmpeg: ffmpeg -i input.avi output.mp4
        
        # Copy file with new extension (mock conversion)
        with open(input_file, 'rb') as infile:
            data = infile.read()
        
        with open(output_file, 'wb') as f:
            f.write(data)
        
        self.temp_files.append(output_file)
        
        return {
            "type": "video",
            "file": output_file,
            "format": input_data.output_format.value,
            "input_format": input_data.input_format.value
        }
    
    async def _perform_frame_extraction(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract frames from video"""
        
        frame_rate = options.get("frame_rate", 1.0)  # 1 frame per second
        max_frames = options.get("max_frames", 10)
        
        frame_files = []
        for i in range(max_frames):
            frame_file = f"{self.working_dir}/frame_{i:04d}.jpg"
            
            # Create mock frame file
            with open(frame_file, 'wb') as f:
                f.write(f'mock_frame_data_{i}'.encode())
            
            frame_files.append(frame_file)
            self.temp_files.append(frame_file)
        
        return {
            "type": "frames",
            "files": frame_files,
            "count": len(frame_files),
            "frame_rate": frame_rate,
            "format": "jpg"
        }
    
    async def _assess_output_quality(
        self, 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess output quality"""
        
        # Basic quality metrics
        if result["type"] == "video":
            return {
                "compression_efficiency": result.get("compression_ratio", 1.0),
                "quality_score": 0.85,  # Mock quality score
                "estimated_psnr": 35.0  # Mock PSNR value
            }
        elif result["type"] == "audio":
            return {
                "bitrate_preservation": 0.9,
                "quality_score": 0.88
            }
        else:
            return {"quality_score": 0.9}
    
    async def _optimize_output(
        self, 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize output if needed"""
        
        # For this implementation, no optimization needed
        return result
    
    async def _generate_output_metadata(
        self, 
        result: Dict[str, Any], 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive output metadata"""
        
        return {
            "operation": input_data.operation.value,
            "input_format": input_data.input_format.value,
            "output_format": result.get("format"),
            "processing_quality": input_data.quality,
            "timestamp": "2024-01-01T00:00:00Z",  # Mock timestamp
            "provider": self.provider_name
        }
    
    async def _read_output_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Read output data from files"""
        
        final_result = result.copy()
        
        if result["type"] in ["video", "audio", "image"]:
            # Read single file
            file_path = result["file"]
            with open(file_path, 'rb') as f:
                final_result["data"] = f.read()
        elif result["type"] == "frames":
            # Read multiple frame files
            frames_data = []
            for file_path in result["files"]:
                with open(file_path, 'rb') as f:
                    frames_data.append(f.read())
            final_result["frames_data"] = frames_data
        
        return final_result
    
    async def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files"""
        
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                # Log warning but don't fail
                pass
        
        # Remove working directory if empty
        try:
            if os.path.exists(self.working_dir):
                os.rmdir(self.working_dir)
        except Exception:
            pass


class FFmpegVideoProcessingTemplate(BaseVideoProcessingTemplate):
    """FFmpeg-specific video processing template"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        super().__init__("ffmpeg", "4.4.0")
        self.ffmpeg_path = ffmpeg_path
    
    async def _initialize_provider(self, input_data: VideoProcessingInput, options: Dict[str, Any]) -> None:
        """Initialize FFmpeg"""
        # Check if FFmpeg is available
        # In practice, run: which ffmpeg or ffmpeg -version
        self.processing_result.add_metadata("ffmpeg_available", True)
    
    async def _perform_transcoding(
        self, 
        input_file: str, 
        input_data: VideoProcessingInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform FFmpeg transcoding"""
        
        output_file = f"{self.working_dir}/transcoded.{input_data.output_format.value}"
        
        # Build FFmpeg command
        quality_params = self._get_quality_params(input_data.quality)
        
        # Mock FFmpeg command execution
        # In practice: subprocess.run([self.ffmpeg_path, '-i', input_file, ...quality_params, output_file])
        
        # Create mock transcoded file
        with open(input_file, 'rb') as infile:
            data = infile.read()
        
        with open(output_file, 'wb') as f:
            f.write(data)  # Mock transcoding
        
        self.temp_files.append(output_file)
        
        self.processing_result.add_metadata("ffmpeg_processing", {
            "command": f"ffmpeg -i {input_file} {' '.join(quality_params)} {output_file}",
            "quality_preset": input_data.quality
        })
        
        return {
            "type": "video",
            "file": output_file,
            "format": input_data.output_format.value,
            "quality": input_data.quality
        }
    
    def _get_quality_params(self, quality: str) -> List[str]:
        """Get FFmpeg quality parameters"""
        
        quality_presets = {
            "low": ["-crf", "28", "-preset", "fast"],
            "medium": ["-crf", "23", "-preset", "medium"],
            "high": ["-crf", "18", "-preset", "slow"],
            "custom": []  # Use custom_params
        }
        
        return quality_presets.get(quality, quality_presets["medium"])


# Register templates in factory
def register_video_processing_templates():
    """Register all video processing templates"""
    
    # FFmpeg templates
    TemplateMethodFactory.register_template(
        "ffmpeg_standard", 
        lambda: FFmpegVideoProcessingTemplate()
    )
    TemplateMethodFactory.register_template(
        "ffmpeg_custom", 
        lambda: FFmpegVideoProcessingTemplate("/usr/local/bin/ffmpeg")
    )