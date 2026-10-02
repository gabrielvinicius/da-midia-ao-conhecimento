"""Rotas de análise: busca por usuário, dono da análise e correção no corpo."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers
from src.text_analysis.api import routers
from src.text_analysis.api.dependencies import (
    get_knowledge_service,
    get_text_analysis_service,
)
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import UserRole

OWNER = uuid4()
OTHER = uuid4()
ANALYSIS_ID = str(uuid4())


class FakeService:
    def __init__(self):
        self.corrected = None
        self.feedback = None

    async def get_analysis(self, query):
        return {"analysis_id": ANALYSIS_ID, "user_id": str(OWNER)}

    async def correct_summary(self, analysis_id, summary):
        self.corrected = summary
        return True

    async def submit_feedback(self, analysis_id, user_id, score, comment=None):
        self.feedback = score
        return True


class FakeKnowledge:
    def __init__(self):
        self.user_id = "not-called"

    async def search(self, query, limit=5, user_id=None):
        self.user_id = user_id
        return []


def _client(user_id, role=UserRole.USER):
    app = FastAPI()
    register_exception_handlers(app)  # como na aplicação: erros de acesso viram 403
    app.include_router(routers.router)
    service, knowledge = FakeService(), FakeKnowledge()
    app.dependency_overrides[get_text_analysis_service] = lambda: service
    app.dependency_overrides[get_knowledge_service] = lambda: knowledge
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=role)
    return TestClient(app), service, knowledge


def test_search_is_restricted_to_the_user_media():
    client, _, knowledge = _client(OWNER)
    assert client.get("/text-analysis/search", params={"query": "regra da cadeia"}).status_code == 200
    assert knowledge.user_id == OWNER


def test_admin_search_covers_all_media():
    client, _, knowledge = _client(OWNER, role=UserRole.ADMIN)
    client.get("/text-analysis/search", params={"query": "regra da cadeia"})
    assert knowledge.user_id is None


def test_long_summary_correction_goes_in_the_body():
    client, service, _ = _client(OWNER)
    long_summary = "# Resumo\n" + "texto " * 5000  # ~30 mil caracteres
    resp = client.put(f"/text-analysis/{ANALYSIS_ID}/summary", json={"summary": long_summary})
    assert resp.status_code == 200
    assert service.corrected == long_summary


def test_legacy_query_parameter_still_works():
    client, service, _ = _client(OWNER)
    resp = client.put(f"/text-analysis/{ANALYSIS_ID}/summary", params={"new_summary": "curto"})
    assert resp.status_code == 200 and service.corrected == "curto"


@pytest.mark.parametrize(
    "method, path, kwargs",
    [
        ("put", f"/text-analysis/{ANALYSIS_ID}/summary", {"json": {"summary": "x"}}),
        ("post", f"/text-analysis/{ANALYSIS_ID}/feedback", {"params": {"score": 1}}),
    ],
)
def test_other_users_cannot_change_the_analysis(method, path, kwargs):
    client, service, _ = _client(OTHER)
    resp = getattr(client, method)(path, **kwargs)
    assert resp.status_code == 403
    assert service.corrected is None and service.feedback is None


def test_missing_summary_is_rejected():
    client, _, _ = _client(OWNER)
    assert client.put(f"/text-analysis/{ANALYSIS_ID}/summary").status_code == 422
