# src/video_processing/infrastructure/providers/ffmpeg_provider.py
"""
FFmpeg video processor - OCP and SRP compliance.
"""
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List
from pathlib import Path

from src.video_processing.domain.interfaces import VideoConfiguration, VideoFormat
from src.video_processing.infrastructure.providers.base_provider import (
    BaseVideoProcessor, 
    VideoProcessorError
)


class FFmpegConfiguration(VideoConfiguration):
    """Configuration for FFmpeg video processing - SRP compliance."""
    
    def __init__(
        self,
        max_file_size: int = 500 * 1024 * 1024,  # 500MB
        max_duration: float = 3600.0,  # 1 hour
        quality_preset: str = "medium",
        audio_bitrate: str = "128k",
        video_bitrate: str = "1000k",
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe"
    ):
        self.max_file_size = max_file_size
        self.max_duration = max_duration
        self.quality_preset = quality_preset
        self.audio_bitrate = audio_bitrate
        self.video_bitrate = video_bitrate
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "max_file_size": self.max_file_size,
            "max_duration": self.max_duration,
            "quality_preset": self.quality_preset,
            "audio_bitrate": self.audio_bitrate,
            "video_bitrate": self.video_bitrate,
            "ffmpeg_path": self.ffmpeg_path,
            "ffprobe_path": self.ffprobe_path
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return (
            self.max_file_size > 0 and
            self.max_duration > 0 and
            bool(self.quality_preset) and
            bool(self.audio_bitrate) and
            bool(self.video_bitrate)
        )
    
    def get_supported_formats(self) -> List[VideoFormat]:
        """Get supported video formats."""
        return [
            VideoFormat.MP4,
            VideoFormat.AVI,
            VideoFormat.MOV,
            VideoFormat.MKV,
            VideoFormat.WEBM,
            VideoFormat.FLV
        ]
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size
    
    def get_max_duration(self) -> float:
        """Get maximum duration in seconds."""
        return self.max_duration


class FFmpegVideoProcessor(BaseVideoProcessor):
    """
    FFmpeg video processor.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: FFmpegConfiguration):
        super().__init__(config)
        self._config = config
    
    def _initialize_processor(self) -> None:
        """Initialize FFmpeg processor."""
        try:
            # Test FFmpeg availability
            import subprocess
            result = subprocess.run(
                [self._config.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise VideoProcessorError("FFmpeg not available or not working")
        except Exception as e:
            raise VideoProcessorError(f"Failed to initialize FFmpeg: {e}") from e
    
    async def _do_validate(self, video_data: bytes) -> bool:
        """Validate video using FFprobe."""
        temp_file_path = None
        try:
            # Save to temporary file
            temp_file_path = await self._save_to_temp_file(video_data)
            
            # Use FFprobe to validate
            command = [
                self._config.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                temp_file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse FFprobe output
                probe_data = json.loads(stdout.decode())
                return self._validate_probe_data(probe_data)
            
            return False
            
        except Exception:
            return False
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    async def _do_extract_info(self, video_data: bytes) -> Dict[str, Any]:
        """Extract video information using FFprobe."""
        temp_file_path = None
        try:
            # Save to temporary file
            temp_file_path = await self._save_to_temp_file(video_data)
            
            # Use FFprobe to get info
            command = [
                self._config.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                temp_file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessorError(f"FFprobe failed: {stderr.decode()}")
            
            probe_data = json.loads(stdout.decode())
            return self._parse_probe_data(probe_data)
            
        except Exception as e:
            raise VideoProcessorError(f"Failed to extract video info: {e}") from e
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    async def _do_extract_audio(self, video_data: bytes) -> bytes:
        """Extract audio using FFmpeg."""
        input_file_path = None
        output_file_path = None
        try:
            # Save video to temporary file
            input_file_path = await self._save_to_temp_file(video_data)
            
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output_file_path = output_file.name
            output_file.close()
            
            # Extract audio using FFmpeg
            command = [
                self._config.ffmpeg_path,
                "-i", input_file_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # PCM audio
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",  # Mono
                "-y",  # Overwrite output
                output_file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessorError(f"FFmpeg audio extraction failed: {stderr.decode()}")
            
            # Read extracted audio
            with open(output_file_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data
            
        except Exception as e:
            raise VideoProcessorError(f"Failed to extract audio: {e}") from e
        finally:
            # Clean up temporary files
            if input_file_path and os.path.exists(input_file_path):
                os.unlink(input_file_path)
            if output_file_path and os.path.exists(output_file_path):
                os.unlink(output_file_path)
    
    async def resize_video(self, video_data: bytes, width: int, height: int) -> bytes:
        """Resize video using FFmpeg."""
        input_file_path = None
        output_file_path = None
        try:
            # Save video to temporary file
            input_file_path = await self._save_to_temp_file(video_data)
            
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            output_file_path = output_file.name
            output_file.close()
            
            # Resize video using FFmpeg
            command = [
                self._config.ffmpeg_path,
                "-i", input_file_path,
                "-vf", f"scale={width}:{height}",
                "-c:a", "copy",  # Copy audio stream
                "-preset", self._config.quality_preset,
                "-y",  # Overwrite output
                output_file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessorError(f"FFmpeg resize failed: {stderr.decode()}")
            
            # Read resized video
            with open(output_file_path, "rb") as f:
                resized_video = f.read()
            
            return resized_video
            
        except Exception as e:
            raise VideoProcessorError(f"Failed to resize video: {e}") from e
        finally:
            # Clean up temporary files
            if input_file_path and os.path.exists(input_file_path):
                os.unlink(input_file_path)
            if output_file_path and os.path.exists(output_file_path):
                os.unlink(output_file_path)
    
    async def compress_video(self, video_data: bytes, quality: str = "medium") -> bytes:
        """Compress video using FFmpeg."""
        input_file_path = None
        output_file_path = None
        try:
            # Save video to temporary file
            input_file_path = await self._save_to_temp_file(video_data)
            
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            output_file_path = output_file.name
            output_file.close()
            
            # Get quality settings
            quality_settings = self._get_quality_settings(quality)
            
            # Compress video using FFmpeg
            command = [
                self._config.ffmpeg_path,
                "-i", input_file_path,
                "-c:v", "libx264",
                "-b:v", quality_settings["video_bitrate"],
                "-c:a", "aac",
                "-b:a", quality_settings["audio_bitrate"],
                "-preset", quality_settings["preset"],
                "-y",  # Overwrite output
                output_file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoProcessorError(f"FFmpeg compression failed: {stderr.decode()}")
            
            # Read compressed video
            with open(output_file_path, "rb") as f:
                compressed_video = f.read()
            
            return compressed_video
            
        except Exception as e:
            raise VideoProcessorError(f"Failed to compress video: {e}") from e
        finally:
            # Clean up temporary files
            if input_file_path and os.path.exists(input_file_path):
                os.unlink(input_file_path)
            if output_file_path and os.path.exists(output_file_path):
                os.unlink(output_file_path)
    
    async def _has_audio_stream(self, video_data: bytes) -> bool:
        """Check if video has audio stream."""
        try:
            info = await self._do_extract_info(video_data)
            streams = info.get("streams", [])
            
            # Look for audio streams
            for stream in streams:
                if stream.get("codec_type") == "audio":
                    return True
            
            return False
        except Exception:
            return False
    
    async def _save_to_temp_file(self, video_data: bytes) -> str:
        """Save video data to temporary file."""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(video_data)
        temp_file.flush()
        temp_file.close()
        return temp_file.name
    
    def _validate_probe_data(self, probe_data: Dict[str, Any]) -> bool:
        """Validate FFprobe data."""
        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])
        
        # Check if we have format info
        if not format_info:
            return False
        
        # Check duration
        duration = float(format_info.get("duration", 0))
        if duration > self._config.get_max_duration():
            return False
        
        # Check if we have at least one video stream
        has_video = any(
            stream.get("codec_type") == "video" 
            for stream in streams
        )
        
        return has_video
    
    def _parse_probe_data(self, probe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FFprobe data into structured info."""
        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])
        
        # Extract format information
        info = {
            "format": format_info.get("format_name", "unknown"),
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "streams": []
        }
        
        # Extract stream information
        for stream in streams:
            stream_info = {
                "codec_type": stream.get("codec_type"),
                "codec_name": stream.get("codec_name"),
                "index": stream.get("index")
            }
            
            if stream_info["codec_type"] == "video":
                stream_info.update({
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "fps": self._parse_frame_rate(stream.get("r_frame_rate", "0/1")),
                    "bitrate": stream.get("bit_rate")
                })
            elif stream_info["codec_type"] == "audio":
                stream_info.update({
                    "sample_rate": stream.get("sample_rate"),
                    "channels": stream.get("channels"),
                    "bitrate": stream.get("bit_rate")
                })
            
            info["streams"].append(stream_info)
        
        return info
    
    def _parse_frame_rate(self, frame_rate_str: str) -> float:
        """Parse frame rate string to float."""
        try:
            if "/" in frame_rate_str:
                num, den = frame_rate_str.split("/")
                return float(num) / float(den)
            return float(frame_rate_str)
        except:
            return 0.0
    
    def _get_quality_settings(self, quality: str) -> Dict[str, str]:
        """Get quality settings for compression."""
        quality_map = {
            "low": {
                "video_bitrate": "500k",
                "audio_bitrate": "64k",
                "preset": "fast"
            },
            "medium": {
                "video_bitrate": self._config.video_bitrate,
                "audio_bitrate": self._config.audio_bitrate,
                "preset": self._config.quality_preset
            },
            "high": {
                "video_bitrate": "2000k",
                "audio_bitrate": "192k",
                "preset": "slow"
            }
        }
        
        return quality_map.get(quality, quality_map["medium"])