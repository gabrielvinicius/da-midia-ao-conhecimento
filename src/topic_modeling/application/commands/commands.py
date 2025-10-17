"""
Topic Modeling Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ProcessTopicModelingCommand:
    """Command to process topic modeling"""
    media_id: str
    text_content: str
    provider: str
    num_topics: Optional[int] = 5


@dataclass(frozen=True)
class AnalyzeTopicsCommand:
    """Command to analyze topics"""
    transcription_id: str
    provider: str
    modeling_options: Optional[Dict[str, Any]] = None