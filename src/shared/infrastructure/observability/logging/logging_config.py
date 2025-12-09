import logging
import structlog
import os
from datetime import datetime
from typing import Any, Dict, Optional


def configure_logging(service_name: str, level: str = "INFO", debug_mode: bool = False) -> None:
    """
    Configures structured logging for the application.
    """
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer() if debug_mode else structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=[logging.StreamHandler()],
    )

    # Example of adding default context for the service
    structlog.get_logger(service_name).bind(service=service_name)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """
    Returns a structured logger instance.
    """
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
