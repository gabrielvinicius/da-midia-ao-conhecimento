# src/sentiment_analysis/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from enum import Enum

# Para referenciar a entidade SentimentAnalysisResult (será criada/corrigida)
# from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult


class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class SentimentProvider(str, Enum):
    HUGGINGFACE = "HUGGINGFACE"
    VADER = "VADER"
    TEXTBLOB = "TEXTBLOB"
    OPENAI = "OPENAI"


class AnalysisGranularity(str, Enum):
    DOCUMENT = "DOCUMENT"
    SENTENCE = "SENTENCE"
    WORD = "WORD"


class ISentimentAnalyzer(ABC):
    """Interface for sentiment analysis operations."""

    @abstractmethod
    async def analyze(self, text_content: str, language: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Performs sentiment analysis on the given text content."""
        pass


class ISentimentAnalysisRepository(ABC):
    """Interface for managing SentimentAnalysisResult entities."""

    @abstractmethod
    async def get_by_id(self, result_id: UUID) -> Optional[Any]: # Usar SentimentAnalysisResult
        """Retrieves a sentiment analysis result by its ID."""
        pass

    @abstractmethod
    async def add(self, result: Any) -> None: # Usar SentimentAnalysisResult
        """Adds a new sentiment analysis result to the repository."""
        pass

    @abstractmethod
    async def update(self, result: Any) -> None: # Usar SentimentAnalysisResult
        """Updates an existing sentiment analysis result in the repository."""
        pass

    @abstractmethod
    async def get_by_media_id(self, media_id: UUID) -> Optional[Any]: # Usar SentimentAnalysisResult
        """Retrieves a sentiment analysis result by its associated media ID."""
        pass


class ISentimentAnalysisTaskScheduler(ABC):
    """Interface for scheduling sentiment analysis tasks."""

    @abstractmethod
    async def schedule_sentiment_analysis_task(self, media_id: str, text_content: str, provider: str, language: str) -> Any:
        """Schedules a sentiment analysis task."""
        pass


class SentimentOperationLogger(ABC):
    """Interface for logging sentiment analysis operations."""

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
        """Log sentiment analysis operation with structured data."""
        pass


class SentimentMetrics(ABC):
    """Interface for recording sentiment analysis metrics."""

    @abstractmethod
    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
        input_text_length_chars: int,
        output_score: float
    ) -> None:
        """Record sentiment analysis operation metrics."""
        pass
