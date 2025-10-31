"""Backwards compatible exports for the summary aggregate."""

from src.summarization.domain.model import SummaryAggregate, SummaryStatus

Summary = SummaryAggregate

__all__ = ["Summary", "SummaryAggregate", "SummaryStatus"]
