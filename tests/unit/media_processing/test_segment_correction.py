"""Correção humana de trechos da transcrição: o texto do modelo fica guardado
e o texto completo passa a usar a correção (a próxima análise já a usa)."""
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
from src.shared.domain.errors import ConflictError, ValidationError
from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import UserRole

OWNER, OTHER = uuid4(), uuid4()


def _completed():
    transcription = Transcription(media_id=uuid4(), user_id=OWNER, language="pt")
    transcription.mark_as_processing()
    transcription.mark_as_completed(
        {
            "text": " Vamos falar de Clean Code. Depois de SOLID.",
            "segments": [
                {"start": 0.0, "end": 4.0, "text": " Vamos falar de clin code."},
                {"start": 4.0, "end": 8.0, "text": " Depois de SOLID."},
            ],
        }
    )
    return transcription


def test_the_correction_keeps_the_model_text_and_rebuilds_the_whole_text():
    transcription = _completed()

    transcription.correct_segment(0, "  Vamos falar de   Clean Code. ")
    transcription.correct_segment(0, "Vamos falar de Clean Code!")

    first = transcription.segments[0]
    assert first["text"] == "Vamos falar de Clean Code!"
    assert first["original_text"] == " Vamos falar de clin code."  # só a primeira versão, a do modelo
    assert (first["start"], first["end"]) == (0.0, 4.0)
    assert transcription.text == "Vamos falar de Clean Code! Depois de SOLID."
    assert transcription.corrected_segments == 1


def test_empty_text_a_missing_segment_or_an_unfinished_transcription_are_refused():
    transcription = _completed()
    with pytest.raises(ValidationError):
        transcription.correct_segment(0, "   ")
    with pytest.raises(ValidationError):
        transcription.correct_segment(5, "texto")
    with pytest.raises(ConflictError):
        Transcription(media_id=uuid4()).correct_segment(0, "texto")


def _client(user_id, role=UserRole.USER):
    transcription = _completed()
    repo = AsyncMock()
    repo.get_by_id.return_value = transcription
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
    return TestClient(app), repo, transcription


def test_the_route_corrects_only_for_the_owner_and_reports_the_count():
    client, repo, transcription = _client(OTHER)
    assert client.put(f"/transcriptions/{transcription.id}/segments/0", json={"text": "x"}).status_code == 404
    repo.save.assert_not_awaited()

    client, _, transcription = _client(OWNER)
    resp = client.put(f"/transcriptions/{transcription.id}/segments/1", json={"text": "Depois, SOLID."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["segments"][1]["text"] == "Depois, SOLID." and body["corrected_segments"] == 1
    assert body["duration"] == 8.0  # sem a duração do arquivo, o fim do último trecho

    assert client.put(f"/transcriptions/{transcription.id}/segments/9", json={"text": "x"}).status_code == 422
