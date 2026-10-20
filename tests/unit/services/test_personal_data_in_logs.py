"""E-mail e texto da busca não vão para os logs."""
import ast
from pathlib import Path

import pytest
import structlog

from src.shared.application.privacy import masked_email

ROOT = Path(__file__).resolve().parents[3]
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}


def _unmasked_email_in_logs(path: Path) -> list[str]:
    """Chamadas de log com ``email=`` que não passa por masked_email."""
    problems = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in LOG_METHODS:
            continue
        for kw in node.keywords:
            masked = (
                isinstance(kw.value, ast.Call)
                and isinstance(kw.value.func, ast.Name)
                and kw.value.func.id == "masked_email"
            )
            if kw.arg == "email" and not masked:
                problems.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return problems


def test_no_log_call_passes_a_raw_email():
    """O main.py registrava o e-mail do primeiro administrador sem máscara."""
    files = [ROOT / "main.py", *sorted((ROOT / "src").rglob("*.py"))]
    problems = [p for f in files for p in _unmasked_email_in_logs(f)]
    assert problems == []


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
