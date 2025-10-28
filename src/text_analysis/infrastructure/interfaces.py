# src/sentiment_analysis/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ISentimentAnalysisService(ABC):
    """Interface for a sentiment analysis service."""

    @abstractmethod
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyzes a block of text and returns the sentiment."""
        pass

class ITopicModelingService(ABC):
    """Interface for a topic modeling or keyword extraction service."""

    @abstractmethod
    def extract_topics(self, text: str, num_topics: int = 10) -> List[str]:
        """Extracts the main topics or keywords from a block of text."""
        pass
