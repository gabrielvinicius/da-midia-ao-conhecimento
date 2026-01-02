"""LLM text generation port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TextGenerationPort(ABC):
    @abstractmethod
    async def summarize_topic(
        self,
        title_hint: Optional[str],
        content: str,
        keywords: list[str],
        language: str,
    ) -> str:
        """Generate a markdown summary for a topic."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the model is available for use."""
