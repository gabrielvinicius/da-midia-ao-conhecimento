# src/summarization/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

from src.summarization.domain.summary import Summary # Para referenciar a entidade Summary

class ISummarizer(ABC):
    """Interface for text summarization operations."""

    @abstractmethod
    async def summarize(self, text_content: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Generates a summary from the given text content."""
        pass

class ISummarizationRepository(ABC):
    """Interface for managing Summary entities."""

    @abstractmethod
    async def get_by_id(self, summary_id: UUID) -> Optional[Summary]:
        """Retrieves a summary by its ID."""
        pass

    @abstractmethod
    async def add(self, summary: Summary) -> None:
        """Adds a new summary to the repository."""
        pass

    @abstractmethod
    async def update(self, summary: Summary) -> None:
        """Updates an existing summary in the repository."""
        pass

    @abstractmethod
    async def get_by_media_id(self, media_id: UUID) -> Optional[Summary]:
        """Retrieves a summary by its associated media ID."""
        pass

class ISummarizationTaskScheduler(ABC):
    """Interface for scheduling summarization tasks."""

    @abstractmethod
    async def schedule_summarization_task(self, media_id: str, text_content: str, provider: str) -> Any:
        """Schedules a summarization task."""
        pass


class SummaryOperationLogger(ABC):
    """Interface for logging summarization operations."""

    @abstractmethod
    async def log_operation(
        self,
        operation: str,
        media_id: str,
        provider: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log summarization operation with structured data."""
        pass


class SummaryMetrics(ABC):
    """Interface for recording summarization metrics."""

    @abstractmethod
    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
        input_length: int,
        output_length: int
    ) -> None:
        """Record summarization operation metrics."""
        pass
