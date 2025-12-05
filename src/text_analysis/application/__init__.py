"""Application layer exports for Text Analysis."""

from .config import AnalysisConfig
from .dto import (
    AnalysisResultDTO,
    SentimentItemDTO,
    TopicDTO,
)
from .service import TextAnalysisService
from .event_handlers import build_text_content_ready_handler
from .metrics import TextAnalysisMetrics, NoOpTextAnalysisMetrics

__all__ = [
    "TextAnalysisService",
    "build_text_content_ready_handler",
    "AnalysisConfig",
    "AnalysisResultDTO",
    "SentimentItemDTO",
    "TopicDTO",
    "TextAnalysisMetrics",
    "NoOpTextAnalysisMetrics",
]
