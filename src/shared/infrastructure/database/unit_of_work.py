"""Unidade de trabalho sobre a sessão do SQLAlchemy.

Fora de uma unidade de trabalho, cada repositório confirma a própria
gravação (operações de um só agregado). Dentro dela, os repositórios só
enviam as mudanças ao banco (flush), e a confirmação ou o desfazer fica com
a unidade de trabalho, para operações que tocam vários repositórios, como a
exclusão de uma mídia e de tudo o que foi derivado dela.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

_DEPTH_KEY = "unit_of_work_depth"


def in_unit_of_work(session) -> bool:
    return bool(getattr(session, "info", {}).get(_DEPTH_KEY))


async def commit(session) -> None:
    """Confirma, ou só envia ao banco se houver uma unidade de trabalho aberta."""
    if in_unit_of_work(session):
        await session.flush()
    else:
        await session.commit()


async def rollback(session) -> None:
    """Desfaz, salvo dentro de uma unidade de trabalho (ela decide ao terminar)."""
    if not in_unit_of_work(session):
        await session.rollback()


class SqlAlchemyUnitOfWork:
    def __init__(self, session) -> None:
        self._session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        info = self._session.info
        outermost = not info.get(_DEPTH_KEY)
        info[_DEPTH_KEY] = info.get(_DEPTH_KEY, 0) + 1
        try:
            yield
        except BaseException:
            info[_DEPTH_KEY] -= 1
            if outermost:
                await self._session.rollback()
            raise
        else:
            info[_DEPTH_KEY] -= 1
            if outermost:
                await self._session.commit()


__all__ = ["SqlAlchemyUnitOfWork", "commit", "in_unit_of_work", "rollback"]
