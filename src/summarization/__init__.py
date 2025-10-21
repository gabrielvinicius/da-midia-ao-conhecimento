# src/summarization/__init__.py
"""
Summarization module following SOLID principles.
"""

# Domain exports
from src.summarization.domain.summary import Summary, SummaryStatus
from src.summarization.domain.interfaces import (
    ISummarizer,
    ISummarizationRepository,
    ISummarizationTaskScheduler
)

__all__ = [
    # Domain
    "Summary",
    "SummaryStatus",
    "ISummarizer",
    "ISummarizationRepository",
    "ISummarizationTaskScheduler",
]
