"""E-mail sem diferença de maiúsculas e limite do bcrypt em bytes."""
import pytest

from src.user_management.application.dtos import CreateUserCommand
from src.user_management.domain.rules import normalize_email
from src.user_management.domain.errors import UserAlreadyExistsError
from src.user_management.infrastructure.dependencies.providers import BcryptPasswordHasher
from src.shared.domain.errors import ConflictError, NotFoundError
from src.user_management.domain.errors import UserNotFoundError


def test_emails_are_compared_without_case():
    assert normalize_email("  Ana@Exemplo.COM ") == "ana@exemplo.com"


@pytest.mark.asyncio
async def test_the_same_email_with_other_case_is_a_conflict():
    from src.user_management.application.auth_queries import UserReadService
    from src.user_management.application.services.user_service import UserService
    from src.user_management.infrastructure.repositories.fake_user_repository import FakeUserRepository

    class Tokens:
        def create_access_token(self, user_id):
            return "a"

        def create_refresh_token(self, user_id):
            return "r"

    repo = FakeUserRepository()
    service = UserService(repo, UserReadService(repo), BcryptPasswordHasher(), Tokens())
    await service.create_user(CreateUserCommand(email="Ana@x.com", password="Senha123"))
    with pytest.raises(UserAlreadyExistsError):
        await service.create_user(CreateUserCommand(email="ana@X.com", password="Senha123"))
    user = await service.authenticate_user("ANA@x.com", "Senha123")
    assert user["user"]["email"] == "ana@x.com"


def test_bcrypt_limit_is_applied_in_bytes_everywhere():
    hasher = BcryptPasswordHasher()
    # 40 letras acentuadas = 80 bytes: o bcrypt só vê os 72 primeiros.
    long_password = "á" * 40
    hashed = hasher.hash(long_password)
    assert hasher.verify(long_password, hashed)
    assert hasher.verify("á" * 36 + "outra coisa", hashed)  # mesmos 72 bytes


def test_passwords_hashed_before_the_switch_from_passlib_still_work():
    """Hashes gravados pelo passlib (bcrypt 3.2) continuam válidos."""
    hasher = BcryptPasswordHasher()
    assert hasher.verify("Senha-antiga-123", "$2b$12$rjLd3ZrEsyeQBuIladxscetIuXfSE8H1QoRxM4gVlcTSYxxqvbToC")
    assert hasher.verify("ção" * 40, "$2b$12$bseh1/89YkkJez4R8SbGFu/Rdh44F8Hnlru48ycc3g5Hmg4JJ9fqe")
    assert not hasher.verify("outra", "$2b$12$rjLd3ZrEsyeQBuIladxscetIuXfSE8H1QoRxM4gVlcTSYxxqvbToC")
    assert not hasher.verify("qualquer", "não-é-um-hash")


def test_user_errors_follow_the_shared_hierarchy():
    assert issubclass(UserAlreadyExistsError, ConflictError)
    assert issubclass(UserNotFoundError, NotFoundError)


def test_creating_a_user_follows_the_same_rules_as_changing_it():
    """Um perfil inválido virava USER sem aviso na criação e era recusado na alteração."""
    from src.user_management.domain import User
    from src.user_management.domain.errors import InvalidUserDataError

    with pytest.raises(InvalidUserDataError):
        User.create(email="ana@ifba.edu.br", password_hash="h", role="SUPERUSER")
    with pytest.raises(InvalidUserDataError):
        User.create(email="sem-arroba", password_hash="h")
    assert User.create(email=" Ana@IFBA.edu.br ", password_hash="h", role="admin").email == "ana@ifba.edu.br"
