"""Input validation helpers for summarization requests."""
from __future__ import annotations


class SummaryValidator:
    """Validate text payloads before dispatching summarization providers."""

    def __init__(self, *, min_text_length: int = 10, max_text_length: int = 10_000) -> None:
        self._min = min_text_length
        self._max = max_text_length

    def validate(self, text: str) -> None:
        if text is None:
            raise ValueError("Text cannot be null")
        length = len(text)
        if length < self._min:
            raise ValueError(f"Text must contain at least {self._min} characters")
        if length > self._max:
            raise ValueError(f"Text exceeds maximum length of {self._max} characters")

