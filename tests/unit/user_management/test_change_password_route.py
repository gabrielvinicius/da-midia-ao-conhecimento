"""PUT /auth/me/password: rota usada pela tela de Configurações."""
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.user_management.api import routers
from src.user_management.api.dependencies import get_current_user
from src.user_management.api.dependencies import get_user_service as dep_get_user_service
from src.shared.infrastructure.exceptions.exception_handlers import register_exception_handlers
from src.user_management.domain.errors import InvalidUserDataError, WrongCurrentPasswordError

USER_ID = uuid4()


class FakeUserService:
    def __init__(self):
        self.calls = []

    async def change_password(self, user_id, old_password, new_password):
        if old_password != "Atual123!":
            raise WrongCurrentPasswordError()
        if not any(c.isdigit() for c in new_password):
            raise InvalidUserDataError("Senha deve conter ao menos um número")
        self.calls.append((user_id, new_password))


def _client():
    app = FastAPI()
    register_exception_handlers(app)  # como em main.py: os erros viram HTTP num só lugar
    app.include_router(routers.router)
    service = FakeUserService()
    app.dependency_overrides[routers.get_user_service] = lambda: service
    app.dependency_overrides[dep_get_user_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=USER_ID)
    return TestClient(app), service


def test_changes_password_of_logged_user():
    client, service = _client()
    resp = client.put("/auth/me/password", json={"old_password": "Atual123!", "new_password": "Nova1234!"})
    assert resp.status_code == 204
    assert service.calls == [(USER_ID, "Nova1234!")]


def test_wrong_current_password_is_rejected():
    client, service = _client()
    resp = client.put("/auth/me/password", json={"old_password": "errada", "new_password": "Nova1234!"})
    assert resp.status_code == 400 and service.calls == []


def test_weak_new_password_is_rejected():
    client, _ = _client()
    resp = client.put("/auth/me/password", json={"old_password": "Atual123!", "new_password": "curta"})
    assert resp.status_code == 422  # barrada pelo esquema da requisição


def test_password_rule_from_the_service_is_a_400():
    """Regra do serviço (aqui, sem número) sai pelo tratador global, sem captura na rota."""
    client, _ = _client()
    resp = client.put("/auth/me/password", json={"old_password": "Atual123!", "new_password": "SemNumeroAqui"})
    assert resp.status_code == 400 and "número" in resp.json()["detail"]
