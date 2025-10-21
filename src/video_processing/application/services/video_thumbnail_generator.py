"""
Video Thumbnail Generator - Essential for video processing pipeline
"""
import structlog
from typing import Dict, Any, Optional
import tempfile
import os
from pathlib import Path

from src.shared.application.unified_services import UnifiedProcessor

logger = structlog.get_logger(__name__)

class VideoThumbnailGenerator(UnifiedProcessor):
    """Generate thumbnails from video files - essential for video pipeline"""
    
    def __init__(self):
        super().__init__("video_thumbnail_generation")
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        self.thumbnail_sizes = {
            'small': (160, 120),
            'medium': (320, 240), 
            'large': (640, 480)
        }
    
    async def _do_process(self, video_data: bytes, **kwargs) -> Dict[str, Any]:
        """Generate thumbnail from video data"""
        filename = kwargs.get('filename', 'video.mp4')
        size = kwargs.get('size', 'medium')
        timestamp = kwargs.get('timestamp', 5.0)  # 5 seconds by default
        
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
            self.logger.error("Thumbnail generation failed", error=str(e), filename=filename)
            raise
    
    async def _generate_with_ffmpeg(self, video_data: bytes, filename: str, 
                                   size: str, timestamp: float) -> bytes:
        """Generate thumbnail using FFmpeg"""
        try:
            import subprocess
            import asyncio
            
            # Get dimensions for size
            width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=Path(filename).suffix, delete=False) as video_temp:
                video_temp.write(video_data)
                video_temp_path = video_temp.name
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as thumb_temp:
                thumb_temp_path = thumb_temp.name
            
            try:
                # FFmpeg command to generate thumbnail
                cmd = [
                    'ffmpeg', '-y',  # -y to overwrite output files
                    '-i', video_temp_path,  # input video
                    '-ss', str(timestamp),  # seek to timestamp
                    '-vframes', '1',  # extract 1 frame
                    '-vf', f'scale={width}:{height}',  # resize
                    '-q:v', '2',  # high quality
                    thumb_temp_path  # output thumbnail
                ]
                
                # Run FFmpeg
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
                
                # Read generated thumbnail
                with open(thumb_temp_path, 'rb') as f:
                    thumbnail_data = f.read()
                
                return thumbnail_data
                
            finally:
                # Cleanup temp files
                if os.path.exists(video_temp_path):
                    os.unlink(video_temp_path)
                if os.path.exists(thumb_temp_path):
                    os.unlink(thumb_temp_path)
                    
        except ImportError:
            self.logger.warning("FFmpeg not available, using fallback method")
            return await self._fallback_thumbnail_generation(video_data, size, timestamp)
        except Exception as e:
            self.logger.error("FFmpeg thumbnail generation failed", error=str(e))
            return await self._fallback_thumbnail_generation(video_data, size, timestamp)
    
    async def _fallback_thumbnail_generation(self, video_data: bytes, 
                                           size: str, timestamp: float) -> bytes:
        """Fallback thumbnail generation without FFmpeg"""
        try:
            # Try using moviepy as fallback
            import moviepy.editor as mp
            from PIL import Image
            import io
            
            # Get dimensions
            width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])
            
            # Write video to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_file.write(video_data)
                temp_path = temp_file.name
            
            try:
                # Extract frame using moviepy
                video = mp.VideoFileClip(temp_path)
                
                # Get frame at timestamp (or midpoint if timestamp > duration)
                duration = video.duration
                actual_timestamp = min(timestamp, duration / 2) if duration else 0
                
                frame = video.get_frame(actual_timestamp)
                video.close()
                
                # Convert to PIL Image and resize
                img = Image.fromarray(frame)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                
                # Convert to JPEG bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                thumbnail_data = img_buffer.getvalue()
                
                return thumbnail_data
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except ImportError:
            self.logger.error("Neither FFmpeg nor moviepy/PIL available for thumbnail generation")
            # Return placeholder thumbnail
            return await self._create_placeholder_thumbnail(size)
        except Exception as e:
            self.logger.error("Fallback thumbnail generation failed", error=str(e))
            return await self._create_placeholder_thumbnail(size)
    
    async def _create_placeholder_thumbnail(self, size: str) -> bytes:
        """Create a placeholder thumbnail when generation fails"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])
            
            # Create placeholder image
            img = Image.new('RGB', (width, height), color='lightgray')
            draw = ImageDraw.Draw(img)
            
            # Add text
            text = "Video\nThumbnail"
            
            # Try to use default font
            try:
                # Use a reasonable font size for the image
                font_size = min(width, height) // 8
                font = ImageFont.load_default()
            except:
                font = None
            
            # Calculate text position (center)
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(text) * 6  # Approximate
                text_height = 20
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Draw text
            draw.text((x, y), text, fill='black', font=font, align='center')
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=85)
            return img_buffer.getvalue()
            
        except ImportError:
            # If PIL is not available, return minimal JPEG header
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    
    async def _get_thumbnail_metadata(self, thumbnail_data: bytes, size: str) -> Dict[str, Any]:
        """Get metadata from generated thumbnail"""
        try:
            width, height = self.thumbnail_sizes.get(size, self.thumbnail_sizes['medium'])
            
            metadata = {
                'size_bytes': len(thumbnail_data),
                'format': 'jpeg',
                'width': width,
                'height': height,
                'aspect_ratio': width / height
            }
            
            # Try to get more detailed metadata if PIL is available
            try:
                from PIL import Image
                import io
                
                img = Image.open(io.BytesIO(thumbnail_data))
                metadata.update({
                    'mode': img.mode,
                    'actual_width': img.width,
                    'actual_height': img.height
                })
            except:
                pass
            
            return metadata
            
        except Exception as e:
            self.logger.warning("Failed to extract thumbnail metadata", error=str(e))
            return {'size_bytes': len(thumbnail_data)}
    
    def get_supported_sizes(self) -> Dict[str, tuple]:
        """Get supported thumbnail sizes"""
        return self.thumbnail_sizes.copy()
    
    def is_supported_format(self, filename: str) -> bool:
        """Check if video format is supported"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.supported_formats