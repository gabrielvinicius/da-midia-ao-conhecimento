# src/shared/infrastructure/logging_config.py
import logging
import structlog
from structlog.types import EventDict, WrappedLogger
from typing import Any
import sys

def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Remover a chave `color_message` do event dict, pois é usada apenas para console.
    """
    event_dict.pop("color_message", None)
    return event_dict

def add_service_context(_, __, event_dict: EventDict) -> EventDict:
    """
    Adiciona contexto global ao log (ex: nome do serviço).
    """
    event_dict["service"] = "video-summarizer"
    return event_dict

def configure_logging(service_name: str = "video-summarizer", level: str = "INFO", debug_mode: bool = False):
    """
    Configura o logging estruturado com structlog.
    
    Args:
        service_name: Nome do serviço para contexto
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        debug_mode: Se True, usa console renderer ao invés de JSON
    """
    # Configurar o nível de logging
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Escolher processadores baseado no modo
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        drop_color_message_key,
        add_service_context,
    ]
    
    # Adicionar renderer apropriado
    if debug_mode:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configuração do logging padrão
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configuração do structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Log de confirmação
    logger = structlog.get_logger(service_name)
    logger.info("Sistema de logging estruturado configurado", level=level, debug_mode=debug_mode)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado para o módulo especificado."""
    return structlog.get_logger(name)


# Configura o logging ao importar este módulo (modo padrão)
configure_logging()
