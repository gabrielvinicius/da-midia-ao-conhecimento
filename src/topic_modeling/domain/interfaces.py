# src/topic_modeling/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

# Para referenciar a entidade TopicModelingResult (será criada/corrigida)
# from src.topic_modeling.domain.topic_modeling import TopicModelingResult


class TopicModelingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ITopicModeler(ABC):
    """Interface for topic modeling operations."""

    @abstractmethod
    async def model_topics(self, text_content: str, language: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Performs topic modeling on the given text content."""
        pass


class ITopicModelingRepository(ABC):
    """Interface for managing TopicModelingResult entities."""

    @abstractmethod
    async def get_by_id(self, result_id: UUID) -> Optional[Any]: # Usar TopicModelingResult
        """Retrieves a topic modeling result by its ID."""
        pass

    @abstractmethod
    async def add(self, result: Any) -> None: # Usar TopicModelingResult
        """Adds a new topic modeling result to the repository."""
        pass

    @abstractmethod
    async def update(self, result: Any) -> None: # Usar TopicModelingResult
        """Updates an existing topic modeling result in the repository."""
        pass

    @abstractmethod
    async def get_by_media_id(self, media_id: UUID) -> Optional[Any]: # Usar TopicModelingResult
        """Retrieves a topic modeling result by its associated media ID."""
        pass


class ITopicModelingTaskScheduler(ABC):
    """Interface for scheduling topic modeling tasks."""

    @abstractmethod
    async def schedule_topic_modeling_task(self, media_id: str, text_content: str, provider: str, language: str) -> Any:
        """Schedules a topic modeling task."""
        pass


class TopicModelingOperationLogger(ABC):
    """Interface for logging topic modeling operations."""

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
        """Log topic modeling operation with structured data."""
        pass


class TopicModelingMetrics(ABC):
    """Interface for recording topic modeling metrics."""

    @abstractmethod
    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        num_topics: int
    ) -> None:
        """Record topic modeling operation metrics."""
        pass
