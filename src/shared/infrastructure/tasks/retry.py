"""Quais erros justificam repetir uma tarefa da fila.

Repetir qualquer exceção fazia um defeito do código rodar o pipeline inteiro
de novo na GPU a cada tentativa. Só se repete o que pode passar sozinho:
banco ou Redis indisponíveis por um momento, tempo esgotado, ou a corrida
entre duas tentativas gravando a mesma análise (a seguinte reaproveita a
gravada).
"""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from src.shared.domain.errors import TemporarilyUnavailableError

try:  # o Redis é opcional nos testes
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    _REDIS_ERRORS: tuple = (RedisConnectionError, RedisTimeoutError)
except ImportError:  # pragma: no cover
    _REDIS_ERRORS = ()

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


__all__ = ["TRANSIENT_ERRORS", "is_transient"]
