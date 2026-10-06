"""E-mail e texto da busca não vão para os logs."""
import pytest
import structlog

from src.shared.application.privacy import masked_email


def test_email_is_masked_but_still_traceable():
    masked = masked_email("Ana.Souza@ifba.edu.br")
    assert masked.startswith("a***@ifba.edu.br#") and "souza" not in masked
    assert masked == masked_email("ana.souza@IFBA.edu.br ")  # mesma conta, mesma marca
    assert masked_email("sem-arroba") == "***"


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
