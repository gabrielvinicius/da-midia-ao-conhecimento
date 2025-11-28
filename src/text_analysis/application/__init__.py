"""Application layer wiring for text analysis."""

from .config import AnalysisConfig
from .dto import AnalysisResultDTO
from .commands.analyze_text import AnalyzeTextCommand, AnalyzeTextCommandHandler
from .queries.get_analysis import GetAnalysisQuery, GetAnalysisQueryHandler
from .queries.list_topics import ListTopicsQuery, ListTopicsQueryHandler
from .service import TextAnalysisService
from .metrics import TextAnalysisMetrics, NoOpTextAnalysisMetrics
from .event_handlers import build_text_content_ready_handler

__all__ = [
    "AnalysisConfig",
    "AnalysisResultDTO",
    "AnalyzeTextCommand",
    "AnalyzeTextCommandHandler",
    "GetAnalysisQuery",
    "GetAnalysisQueryHandler",
    "ListTopicsQuery",
    "ListTopicsQueryHandler",
    "TextAnalysisService",
    "TextAnalysisMetrics",
    "NoOpTextAnalysisMetrics",
    "build_text_content_ready_handler",
]
