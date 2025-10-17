"""
Sentiment Analysis Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class AnalyzeSentimentCommand:
    """Command to analyze sentiment"""
    text_content: str
    media_id: str
    provider: str
    language: Optional[str] = "en"


@dataclass(frozen=True)
class ProcessSentimentAnalysisCommand:
    """Command to process sentiment analysis for media"""
    media_id: str
    transcription_id: str
    provider: str
    analysis_options: Optional[Dict[str, Any]] = None