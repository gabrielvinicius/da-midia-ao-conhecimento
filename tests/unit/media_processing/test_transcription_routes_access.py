"""Rotas de transcrição: só o dono da mídia (ou um admin) acessa."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.media_management.api.dependencies import get_media_service
from src.media_processing.api import routers
from src.media_processing.api.dependencies import get_transcription_service
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import UserRole

OWNER, OTHER = uuid4(), uuid4()
MEDIA_ID, TRANSCRIPTION_ID = uuid4(), uuid4()


class FakeTranscriptionService:
    def __init__(self):
        self.aliases_set = False

    def _transcription(self):
        return SimpleNamespace(
            id=TRANSCRIPTION_ID, media_id=MEDIA_ID, text="oi", language="pt",
            status=SimpleNamespace(value="completed"), confidence_score=None,
            created_at=datetime.now(timezone.utc), processed_at=None, speaker_aliases={}, segments=[],
            error_message=None,
        )

    async def get_transcription_by_id(self, query):
        return self._transcription()

    async def get_transcription_by_media_id(self, query):
        return self._transcription()

    async def set_speaker_aliases(self, command):
        self.aliases_set = True
        return {}


class FakeMediaService:
    async def get_media(self, query):
        return SimpleNamespace(id=MEDIA_ID, user_id=OWNER)


def _client(user_id, role=UserRole.USER):
    app = FastAPI()
    app.include_router(routers.router)
    service = FakeTranscriptionService()
    app.dependency_overrides[get_transcription_service] = lambda: service
    app.dependency_overrides[get_media_service] = lambda: FakeMediaService()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role=role)
    return TestClient(app), service


READS = [
    ("get", "/transcriptions/", {"params": {"media_id": str(MEDIA_ID)}}),
    ("get", f"/transcriptions/{TRANSCRIPTION_ID}", {}),
]
WRITE = ("put", f"/transcriptions/{TRANSCRIPTION_ID}/speaker-aliases", {"json": {"aliases": {"SPEAKER_0": "Ana"}}})


@pytest.mark.parametrize("method, path, kwargs", READS + [WRITE])
def test_other_users_are_denied(method, path, kwargs):
    client, service = _client(OTHER)
    # 404, e não 403: quem não é dono não descobre que a mídia existe.
    assert getattr(client, method)(path, **kwargs).status_code == 404
    assert service.aliases_set is False


@pytest.mark.parametrize("method, path, kwargs", READS)
def test_owner_and_admin_can_read(method, path, kwargs):
    for user, role in [(OWNER, UserRole.USER), (OTHER, UserRole.ADMIN)]:
        client, _ = _client(user, role)
        assert getattr(client, method)(path, **kwargs).status_code == 200
