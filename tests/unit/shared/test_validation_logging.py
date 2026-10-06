"""Erros de validação não levam o que o usuário enviou (senhas) ao log."""
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr

from src.shared.infrastructure.middleware.validation_middleware import register_validation_middleware


class Cadastro(BaseModel):
    email: EmailStr
    password: str


def test_password_never_reaches_the_log_or_the_response():
    app = FastAPI()
    register_validation_middleware(app)

    @app.post("/cadastro")
    async def cadastro(body: Cadastro):
        return {}

    with structlog.testing.capture_logs() as logs:
        r = TestClient(app).post("/cadastro", json={"email": "nao-e-email", "password": "MinhaSenhaSecreta123"})

    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "email"]
    assert "MinhaSenhaSecreta123" not in r.text
    assert "MinhaSenhaSecreta123" not in repr(logs)
    assert logs and logs[0]["event"] == "http.request.validation_failed"
