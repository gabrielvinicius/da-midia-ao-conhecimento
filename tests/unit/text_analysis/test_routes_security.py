"""Rotas de análise: busca por usuário, dono da análise, correção e pedido de análise."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers
from src.text_analysis.api import routers
from src.text_analysis.api.dependencies import (
    get_analysis_read_service,
    get_analysis_request_service,
    get_analysis_review_service,
    get_knowledge_service,
)
from src.text_analysis.application.ports.transcription_port import TextSourceData
from src.text_analysis.application.services.analysis_request_service import AnalysisRequestService
from src.text_analysis.application.services.analysis_review_service import AnalysisReviewService
from src.text_analysis.domain import Analysis, Document, Topic
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import UserRole

OWNER = uuid4()
OTHER = uuid4()
MEDIA_ID = uuid4()


class FakeKnowledge:
    def __init__(self):
        self.user_id = "not-called"

    async def search(self, query, limit=5, user_id=None):
        self.user_id = user_id
        return []


class FakeFeedback:
    def __init__(self):
        self.saved = None

    async def save_feedback(self, analysis_id, user_id, score, comment=None):
        self.saved = (score, comment)


class FakeSources:
    def __init__(self, text="texto da aula"):
        self.text = text

    async def get_media_owner(self, media_id):
        return OWNER if media_id == MEDIA_ID else None

    async def get_text_source(self, media_id):
        return TextSourceData(id=uuid4(), text=self.text, language="pt", segments=[], media_id=media_id)


class FakeQueue:
    def __init__(self):
        self.payloads = []

    def request_analysis(self, payload):
        self.payloads.append(payload)


async def _seed(repo):
    analysis = Analysis.new(Document.from_payload("x"), media_id=MEDIA_ID, user_id=OWNER)
    analysis.summary = "original"
    await repo.save(analysis)
    return analysis


def _client(user_id, role=UserRole.USER, text="texto da aula"):
    import asyncio

    repo, feedback, queue, knowledge = InMemoryAnalysisRepository(), FakeFeedback(), FakeQueue(), FakeKnowledge()
    analysis = asyncio.run(_seed(repo))
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routers.router)
    from src.text_analysis.application.services.text_analysis_read_service import TextAnalysisReadService

    app.dependency_overrides[get_analysis_read_service] = lambda: TextAnalysisReadService(repo)
    app.dependency_overrides[get_analysis_review_service] = lambda: AnalysisReviewService(repo, feedback)
    app.dependency_overrides[get_analysis_request_service] = lambda: AnalysisRequestService(FakeSources(text), queue, repo)
    app.dependency_overrides[get_knowledge_service] = lambda: knowledge
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=role)
    return TestClient(app), SimpleNamespace(
        analysis=analysis, feedback=feedback, queue=queue, knowledge=knowledge
    )


def test_search_is_restricted_to_the_user_media():
    client, ctx = _client(OWNER)
    assert client.get("/text-analysis/search", params={"query": "regra da cadeia"}).status_code == 200
    assert ctx.knowledge.user_id == OWNER


def test_admin_search_covers_all_media():
    client, ctx = _client(OWNER, role=UserRole.ADMIN)
    client.get("/text-analysis/search", params={"query": "regra da cadeia"})
    assert ctx.knowledge.user_id is None


def test_long_summary_correction_goes_in_the_body():
    client, ctx = _client(OWNER)
    long_summary = "# Resumo\n" + "texto " * 5000  # ~30 mil caracteres
    resp = client.put(f"/text-analysis/{ctx.analysis.id}/summary", json={"summary": long_summary})
    assert resp.status_code == 200
    assert ctx.analysis.summary == long_summary
    assert ctx.analysis.diagnostics["original_ai_summary"] == "original"


def test_feedback_goes_in_the_body():
    client, ctx = _client(OWNER)
    resp = client.post(f"/text-analysis/{ctx.analysis.id}/feedback", json={"score": -1, "comment": "faltou um tema"})
    assert resp.status_code == 200 and ctx.feedback.saved == (-1, "faltou um tema")


@pytest.mark.parametrize("method, suffix, body", [("put", "summary", {"summary": "x"}), ("post", "feedback", {"score": 1})])
def test_other_users_get_404_and_change_nothing(method, suffix, body):
    """404, como nas mídias: um 403 confirmaria que a análise existe."""
    client, ctx = _client(OTHER)
    resp = getattr(client, method)(f"/text-analysis/{ctx.analysis.id}/{suffix}", json=body)
    assert resp.status_code == 404
    assert ctx.analysis.summary == "original" and ctx.feedback.saved is None
    assert client.get(f"/text-analysis/{ctx.analysis.id}").status_code == 404


def test_invalid_ids_are_rejected_not_500():
    client, _ = _client(OWNER)
    assert client.post("/text-analysis/nao-e-um-id/feedback", json={"score": 1}).status_code == 422
    assert client.put("/text-analysis/nao-e-um-id/summary", json={"summary": "x"}).status_code == 422


def test_missing_summary_is_rejected():
    client, ctx = _client(OWNER)
    assert client.put(f"/text-analysis/{ctx.analysis.id}/summary").status_code == 422


def test_analysis_is_queued_for_the_worker_not_run_in_the_api():
    client, ctx = _client(OWNER)
    resp = client.post("/text-analysis/analyze", json={"media_id": str(MEDIA_ID)})
    assert resp.status_code == 202
    [payload] = ctx.queue.payloads
    assert payload["media_id"] == str(MEDIA_ID) and payload["user_id"] == str(OWNER)
    assert "text" not in payload  # o worker lê o texto da transcrição


def test_analysis_request_checks_owner_and_text():
    other, ctx = _client(OTHER)
    assert other.post("/text-analysis/analyze", json={"media_id": str(MEDIA_ID)}).status_code == 404
    assert ctx.queue.payloads == []

    not_ready, ctx = _client(OWNER, text="")
    assert not_ready.post("/text-analysis/analyze", json={"media_id": str(MEDIA_ID)}).status_code == 409
    assert ctx.queue.payloads == []


@pytest.mark.parametrize("field", ["original_ai_summary", "original_ai_chapters", "original_ai_review_questions", "topic"])
def test_a_new_analysis_is_refused_without_erasing_reviewed_content(field):
    client, ctx = _client(OWNER)
    if field == "topic":
        ctx.analysis.topics = [Topic(id=0, keywords=[], title="Tema revisado", original_title="Tema da IA")]
    else:
        ctx.analysis.diagnostics[field] = "original" if field == "original_ai_summary" else []
    ctx.analysis.summary = "Resumo revisado."

    response = client.post("/text-analysis/analyze", json={"media_id": str(MEDIA_ID)})

    assert response.status_code == 409
    assert ctx.queue.payloads == []
    assert ctx.analysis.summary == "Resumo revisado."
