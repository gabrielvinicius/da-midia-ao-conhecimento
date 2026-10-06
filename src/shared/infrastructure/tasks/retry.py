"""Quando repetir uma tarefa da fila.

Duas políticas, conforme o custo de repetir:

- Transcrição e extração de texto repetem tudo o que não for definitivo
  (``is_permanent_failure``): a falta de memória na GPU ou uma leitura que
  falhou podem passar na tentativa seguinte. Antes, a transcrição repetia
  até um "mídia não encontrada", e a extração não repetia nem uma
  dependência fora do ar.
- A análise repete só o que passa sozinho (``TRANSIENT_ERRORS``): banco ou
  Redis indisponíveis por um momento, tempo esgotado, ou a corrida entre duas
  tentativas gravando a mesma análise (a seguinte reaproveita a gravada).
  Repetir qualquer exceção rodava o pipeline inteiro de novo na GPU a cada
  defeito do código.
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from src.shared.domain.errors import TemporarilyUnavailableError, is_permanent_failure

try:  # o Redis é opcional nos testes
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    _REDIS_ERRORS: tuple = (RedisConnectionError, RedisTimeoutError)
except ImportError:  # pragma: no cover
    _REDIS_ERRORS = ()

# Tentativas além da primeira. Cada uma pode ocupar a GPU por muito tempo.
PIPELINE_MAX_RETRIES = 3
# Espera antes da tentativa n (1, 2, 3...): 30 s, 60 s, 120 s, até 10 min.
RETRY_BASE_SECONDS = 30
RETRY_MAX_SECONDS = 600

TRANSIENT_ERRORS: tuple = (
    OperationalError,
    InterfaceError,
    IntegrityError,
    ConnectionError,
    TimeoutError,
    TemporarilyUnavailableError,
    *_REDIS_ERRORS,
)


def is_transient(exc: BaseException) -> bool:
    return isinstance(exc, TRANSIENT_ERRORS)


def is_final_attempt(task) -> bool:
    """Esta é a última tentativa: uma falha agora é a definitiva."""
    return (task.request.retries or 0) >= (task.max_retries or 0)


def retry_unless_permanent(task, exc: BaseException) -> None:
    """Agenda outra tentativa, com espera crescente, para o erro que pode
    passar. Para o definitivo, ou na última tentativa, não faz nada: quem
    chamou deixa o erro subir e a tarefa termina com falha."""
    if is_permanent_failure(exc) or is_final_attempt(task):
        return
    countdown = min(RETRY_BASE_SECONDS * 2 ** (task.request.retries or 0), RETRY_MAX_SECONDS)
    raise task.retry(exc=exc, countdown=countdown)


__all__ = [
    "PIPELINE_MAX_RETRIES",
    "TRANSIENT_ERRORS",
    "is_final_attempt",
    "is_transient",
    "retry_unless_permanent",
]
