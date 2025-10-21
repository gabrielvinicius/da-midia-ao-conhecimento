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
