"""Rotas de transcrição: só o dono da mídia (ou um admin) acessa; os demais veem 404."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.media_processing.api import routers
from src.media_processing.api.dependencies import get_transcription_service
from src.media_processing.application.services.transcription_service import TranscriptionService
from src.media_processing.domain import Transcription
from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import UserRole

OWNER, OTHER = uuid4(), uuid4()
TRANSCRIPTION = Transcription(media_id=uuid4(), user_id=OWNER, text="oi", language="pt")


def _client(user_id, role=UserRole.USER):
    repo = AsyncMock()
    repo.get_by_id.return_value = TRANSCRIPTION
    repo.get_by_media_id.return_value = TRANSCRIPTION
    repo.save.side_effect = lambda t: t
    service = TranscriptionService(
        transcription_repo=repo, task_scheduler=None, transcription_logger=AsyncMock(),
        transcription_metrics=AsyncMock(),
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routers.router)
    app.dependency_overrides[get_transcription_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=role)
    return TestClient(app), repo


READS = [
    ("get", "/transcriptions/", {"params": {"media_id": str(TRANSCRIPTION.media_id)}}),
    ("get", f"/transcriptions/{TRANSCRIPTION.id}", {}),
]
WRITE = ("put", f"/transcriptions/{TRANSCRIPTION.id}/speaker-aliases", {"json": {"aliases": {"SPEAKER_0": "Ana"}}})


@pytest.mark.parametrize("method, path, kwargs", READS + [WRITE])
def test_other_users_get_404(method, path, kwargs):
    client, repo = _client(OTHER)
    # 404, e não 403: quem não é dono não descobre que a mídia existe.
    assert getattr(client, method)(path, **kwargs).status_code == 404
    repo.save.assert_not_awaited()


@pytest.mark.parametrize("method, path, kwargs", READS + [WRITE])
def test_owner_and_admin_can_use_them(method, path, kwargs):
    for user, role in [(OWNER, UserRole.USER), (OTHER, UserRole.ADMIN)]:
        client, _ = _client(user, role)
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 200 and resp.json()["media_id"] == str(TRANSCRIPTION.media_id)


def test_speaker_names_return_the_transcription():
    """A interface guarda a resposta como a transcrição; antes vinha num envelope."""
    client, _ = _client(OWNER)
    resp = client.put(*WRITE[1:2], **WRITE[2])
    assert resp.json()["speaker_aliases"] == {"SPEAKER_0": "Ana"}
