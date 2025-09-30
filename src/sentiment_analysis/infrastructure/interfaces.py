# src/sentiment_analysis/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class ISentimentAnalysisService(ABC):
    """Interface for a sentiment analysis service."""

    @abstractmethod
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyzes a block of text and returns the sentiment.

        Args:
            text: The input text to analyze.

        Returns:
            A dictionary containing the sentiment result, typically with keys
            like 'label' (e.g., 'POSITIVE') and 'score'.
        """
        pass
