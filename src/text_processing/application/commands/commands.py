"""
Text Processing Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ProcessTextCommand:
    """Command to process text"""
    media_id: str
    text_content: str
    processing_type: str
    options: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ExtractTextCommand:
    """Command to extract text from media"""
    media_id: str
    file_path: str
    extraction_method: str