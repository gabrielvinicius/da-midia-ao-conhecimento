"""
Text Processing Domain Interfaces - Defines contracts for text processing operations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class ITextProcessor(ABC):
    """Interface for text processing operations."""

    @abstractmethod
    async def process_text(self, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processes text content based on the specified type and options."""
        pass


class ITextExtractor(ABC):
    """Interface for extracting text from various sources."""

    @abstractmethod
    async def extract_text(self, file_path: str, extraction_method: str) -> str:
        """Extracts text from a given file path using a specified method."""
        pass


class ITextProcessingTaskScheduler(ABC):
    """Interface for scheduling text processing tasks."""

    @abstractmethod
    async def schedule_process_text_task(self, media_id: str, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Any:
        """Schedules a text processing task."""
        pass
