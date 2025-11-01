import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.user_management.application.user_service import UserService
from src.user_management.config.settings import AuthSettings
from src.user_management.domain.user import User, UserRole
from src.shared.utils.password_utils import hash_password, verify_password


@pytest.fixture
def settings() -> AuthSettings:
    return AuthSettings(password_min_length=8)


@pytest.fixture
def repository_mock():
    repo = AsyncMock()
    repo.find_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda user: user)
    repo.find_by_id = AsyncMock(return_value=None)
    repo.list_all = AsyncMock(return_value=[])
    repo.delete = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def user_service(repository_mock, settings) -> UserService:
    return UserService(user_repository=repository_mock, settings=settings)


@pytest.mark.asyncio
async def test_create_user_hashes_password(repository_mock, user_service):
    user = await user_service.create_user("demo@example.com", "StrongPass1", role="admin")

    repository_mock.find_by_email.assert_awaited_once_with("demo@example.com")
    repository_mock.save.assert_awaited()
    assert user.email == "demo@example.com"
    assert user.role == UserRole.ADMIN
    # password must be hashed, not plain text
    assert user.password_hash != "StrongPass1"


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate(repository_mock, user_service):
    repository_mock.find_by_email.return_value = User(
        id=uuid4(),
        email="demo@example.com",
        password_hash="hashed",
        role=UserRole.USER,
    )

    with pytest.raises(ValueError):
        await user_service.create_user("demo@example.com", "StrongPass1")


@pytest.mark.asyncio
async def test_authenticate_user_returns_token(repository_mock, user_service):
    password = "StrongPass1"
    hashed = hash_password(password)
    user = User(id=uuid4(), email="demo@example.com", password_hash=hashed, role=UserRole.USER)
    repository_mock.find_by_email.return_value = user

    result = await user_service.authenticate_user("demo@example.com", password)

    assert "token" in result and result["token"]
    assert result["user"]["email"] == "demo@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(repository_mock, user_service):
    user = User(id=uuid4(), email="demo@example.com", password_hash=hash_password("StrongPass1"), role=UserRole.USER)
    repository_mock.find_by_email.return_value = user

    with pytest.raises(ValueError):
        await user_service.authenticate_user("demo@example.com", "WrongPass")


@pytest.mark.asyncio
async def test_update_user_role(repository_mock, user_service):
    user = User(id=uuid4(), email="demo@example.com", password_hash="hash", role=UserRole.USER)
    repository_mock.find_by_id.return_value = user

    updated = await user_service.update_user_role(user.id, "admin")

    assert updated.role == UserRole.ADMIN
    repository_mock.save.assert_awaited()


@pytest.mark.asyncio
async def test_activate_and_deactivate_user(repository_mock, user_service):
    user = User(id=uuid4(), email="demo@example.com", password_hash="hash", role=UserRole.USER, is_active=False)
    repository_mock.find_by_id.return_value = user

    activated = await user_service.activate_user(user.id)
    assert activated.is_active is True

    repository_mock.find_by_id.return_value = activated
    deactivated = await user_service.deactivate_user(user.id)
    assert deactivated.is_active is False


@pytest.mark.asyncio
async def test_change_password(repository_mock, user_service):
    user = User(id=uuid4(), email="demo@example.com", password_hash=hash_password("OldPass1"), role=UserRole.USER)
    repository_mock.find_by_id.return_value = user

    await user_service.change_password(user.id, "OldPass1", "NewPass1")

    repository_mock.save.assert_awaited()
    assert verify_password("NewPass1", user.password_hash)
    assert not verify_password("OldPass1", user.password_hash)



@pytest.mark.asyncio
async def test_delete_user(repository_mock, user_service):
    user = User(id=uuid4(), email="demo@example.com", password_hash="hash", role=UserRole.USER)
    repository_mock.find_by_id.return_value = user

    await user_service.delete_user(user.id)

    repository_mock.delete.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_list_users(repository_mock, user_service):
    repository_mock.list_all.return_value = ["item"]

    result = await user_service.list_users(page=2, limit=5, search="demo")

    repository_mock.list_all.assert_awaited_once_with(page=2, limit=5, search="demo")
    assert result == ["item"]

