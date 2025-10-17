"""
Video Processing Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ProcessVideoCommand:
    """Command to process video"""
    media_id: str
    video_path: str
    processing_type: str
    output_format: Optional[str] = None
    quality_settings: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ExtractAudioCommand:
    """Command to extract audio from video"""
    media_id: str
    video_path: str
    audio_format: str = "wav"
    quality: Optional[str] = "high"