"""Cada erro de aplicação vira um código HTTP, num único lugar."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.media_management.application.errors import InvalidUploadError, MediaDataErasureError
from src.media_management.domain import MediaNotReprocessableError
from src.shared.domain.errors import (
    AccessDeniedError,
    DomainError,
    NotFoundError,
    ResourceNotFoundError,
)
from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers


@pytest.mark.parametrize(
    "error, status",
    [
        (NotFoundError("não existe"), 404),
        (ResourceNotFoundError("Media", "1"), 404),
        (AccessDeniedError("negado"), 403),
        (MediaNotReprocessableError("concluída"), 409),
        (MediaDataErasureError("tente de novo"), 503),
        (DomainError("regra"), 400),
        (InvalidUploadError("formato"), 400),
    ],
)
def test_application_errors_map_to_http(error, status):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/x")
    async def boom():
        raise error

    response = TestClient(app).get("/x")
    assert response.status_code == status
    assert response.json()["detail"] == str(error)  # o campo que a interface lê


def test_unexpected_errors_do_not_leak_internal_messages():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/x")
    async def boom():
        raise RuntimeError("senha do banco: segredo")

    response = TestClient(app, raise_server_exceptions=False).get("/x")
    assert response.status_code == 500
    assert "segredo" not in response.text
