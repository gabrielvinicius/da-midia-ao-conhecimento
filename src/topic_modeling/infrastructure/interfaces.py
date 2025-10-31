# src/topic_modeling/infrastructure/interfaces.py
from abc import ABC, abstractmethod
from typing import List

class ITopicModelingService(ABC):
    """Interface for a topic modeling or keyword extraction service."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the name of the topic modeling provider."""
        pass

    @abstractmethod
    def extract_topics(self, text: str, num_topics: int = 5, num_words: int = 5) -> List[str]:
        """Extracts the main topics or keywords from a block of text."""
        pass
