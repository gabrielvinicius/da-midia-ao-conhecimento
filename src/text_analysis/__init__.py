"""Public API for text_analysis bounded context."""

from .application import TextAnalysisService, build_text_content_ready_handler

__all__ = [
    "TextAnalysisService",
    "build_text_content_ready_handler",
]
