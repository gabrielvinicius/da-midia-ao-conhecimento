"""E-mail, endereço IP e texto da busca não vão para os logs."""
import pytest
import structlog

from src.shared.application.privacy import masked_email, masked_ip


def test_email_is_masked_but_still_traceable():
    masked = masked_email("Ana.Souza@ifba.edu.br")
    assert masked.startswith("a***@ifba.edu.br#") and "souza" not in masked
    assert masked == masked_email("ana.souza@IFBA.edu.br ")  # mesma conta, mesma marca
    assert masked_email("sem-arroba") == "***"


def test_ip_is_masked_but_still_traceable():
    masked = masked_ip("203.0.113.42")
    assert masked.startswith("203.0.x.x#") and "113" not in masked
    assert masked == masked_ip(" 203.0.113.42")  # mesma origem, mesma marca
    assert masked != masked_ip("203.0.113.43")
    assert masked_ip("2001:db8::1").startswith("2001:x#")
    assert masked_ip(None) == "***"


def test_throttled_login_log_does_not_contain_the_ip():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.user_management.api.dependencies import get_auth_service, get_auth_settings, get_login_throttle
    from src.user_management.api.routers import router

    class Throttle:
        async def retry_after(self, email, ip):
            return 600

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_login_throttle] = lambda: Throttle()
    app.dependency_overrides[get_auth_service] = lambda: None
    app.dependency_overrides[get_auth_settings] = lambda: None

    with structlog.testing.capture_logs() as logs:
        response = TestClient(app).post(
            "/auth/token",
            data={"username": "ana@ifba.edu.br", "password": "x"},
            headers={"X-Real-IP": "203.0.113.42"},
        )
    assert response.status_code == 429
    throttled = [entry for entry in logs if entry.get("event") == "auth.login.throttled"]
    assert throttled and all("203.0.113.42" not in str(entry) for entry in throttled)


@pytest.mark.asyncio
async def test_login_logs_do_not_contain_the_email():
    from src.user_management.application.services.auth_service import AuthService
    from src.user_management.domain.errors import InvalidCredentialsError

    class Users:
        async def authenticate_user(self, email, password):
            raise InvalidCredentialsError()

    with structlog.testing.capture_logs() as logs, pytest.raises(InvalidCredentialsError):
        await AuthService(Users(), settings=None).authenticate_user("ana@ifba.edu.br", "x")
    assert logs and all("ana@ifba.edu.br" not in str(entry) for entry in logs)


@pytest.mark.asyncio
async def test_search_logs_do_not_contain_the_question():
    from src.text_analysis.application.services.knowledge_base_service import KnowledgeBaseService

    class Embedder:
        def embed(self, texts, kind="passage"):
            return [[0.1]]

    class Repo:
        async def semantic_search(self, vector, limit, user_id=None):
            return []

    with structlog.testing.capture_logs() as logs:
        await KnowledgeBaseService(Repo(), Embedder()).search("minha nota na prova de cálculo")
    assert all("prova de cálculo" not in str(entry) for entry in logs)
