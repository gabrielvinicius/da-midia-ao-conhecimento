import logging
import os
from typing import Optional

import structlog

# "json" (padrão, para coleta) ou "console" (leitura humana no desenvolvimento).
LOG_FORMAT_ENV = "LOG_FORMAT"
LOG_LEVEL_ENV = "LOG_LEVEL"


def configure_logging(service_name: str, level: Optional[str] = None, log_format: Optional[str] = None) -> None:
    """Configura o log estruturado da API e dos workers.

    O ``merge_contextvars`` inclui em cada linha o que foi associado ao
    contexto (o ``correlation_id`` da requisição ou da tarefa).
    """
    level = (level or os.getenv(LOG_LEVEL_ENV, "INFO")).upper()
    log_format = (log_format or os.getenv(LOG_FORMAT_ENV, "json")).lower()
    def add_service(_logger, _method, event_dict):
        event_dict.setdefault("service", service_name)
        return event_dict

    renderer = structlog.dev.ConsoleRenderer() if log_format == "console" else structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_service,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", level=level, handlers=[logging.StreamHandler()], force=True)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Returns a structured logger instance."""
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
