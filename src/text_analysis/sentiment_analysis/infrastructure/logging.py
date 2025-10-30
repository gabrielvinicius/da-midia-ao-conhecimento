"""Structured logging helpers for sentiment analysis operations."""

import structlog


class StructuredSentimentLogger:
    """Small wrapper around ``structlog`` providing semantic helpers."""

    def __init__(self, logger_name: str = "sentiment_analysis") -> None:
        self._logger = structlog.get_logger(logger_name)

    def info(self, event: str, **kwargs) -> None:
        self._logger.info(event, **kwargs)

    def error(self, event: str, **kwargs) -> None:
        self._logger.error(event, **kwargs)

    def log_operation(self, operation: str, success: bool, duration: float, **kwargs) -> None:
        self._logger.info(
            "sentiment_analysis.operation",
            operation=operation,
            success=success,
            duration=duration,
            **kwargs,
        )


__all__ = ["StructuredSentimentLogger"]

