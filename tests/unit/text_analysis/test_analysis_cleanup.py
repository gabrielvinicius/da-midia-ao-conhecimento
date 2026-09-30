"""A limpeza da análise precisa apagar os trechos indexados antes da mídia."""
from uuid import uuid4

import pytest

from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


class _Result:
    def scalars(self):
        return self

    def all(self):
        return []


class _FakeSession:
    def __init__(self):
        self.statements = []
        self.committed = False

    async def execute(self, stmt, *args):
        self.statements.append(str(stmt))
        return _Result()

    async def delete(self, record):
        pass

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_delete_by_media_id_also_removes_knowledge_chunks():
    session = _FakeSession()
    await SqlAlchemyAnalysisRepository(session).delete_by_media_id(uuid4())

    assert session.statements[0].startswith("DELETE FROM knowledge_chunks")
    assert session.committed
