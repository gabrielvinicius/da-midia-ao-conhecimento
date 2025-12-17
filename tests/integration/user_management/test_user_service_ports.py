
import pytest

from src.user_management.application.dtos import (
    CreateUserCommand,
    DeleteUserCommand,
)
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.user_service import UserService
from src.user_management.domain import User, UserRole


class FakeUserRepo:
    def __init__(self):
        self.saved = {}

    async def find_by_id(self, user_id):
        return self.saved.get(user_id)

    async def find_by_email(self, email):
        for u in self.saved.values():
            if u.email == email:
                return u
        return None

    async def list_all(self, *, page: int, limit: int, search):
        return list(self.saved.values())

    async def count_all(self):
        return len(self.saved)

    async def count_active(self):
        return sum(1 for u in self.saved.values() if u.is_active)

    async def count_filtered(self, *, search):
        return len(await self.list_all(page=1, limit=1000, search=search))

    async def save(self, user: User) -> User:
        self.saved[user.id] = user
        return user

    async def delete(self, user_id):
        return bool(self.saved.pop(user_id, None))

    # Ports expected by UserReadService (pass-through helpers)
    async def get_by_id(self, user_id):
        return await self.find_by_id(user_id)

    async def get_by_email(self, email):
        return await self.find_by_email(email)


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"hashed:{password}"


class FakeTokenProvider:
    def create_access_token(self, user_id):
        return f"token-{user_id}"

    def verify_token(self, token: str):
        return {"sub": token.removeprefix("token-")}


@pytest.mark.integration
@pytest.mark.anyio
async def test_user_service_register_and_delete():
    repo = FakeUserRepo()
    read_service = UserReadService(user_repository=repo)
    service = UserService(
        user_repository=repo,
        user_read_service=read_service,
        password_hasher=FakeHasher(),
        token_provider=FakeTokenProvider(),
        settings=None,
    )

    create_cmd = CreateUserCommand(email="u@test.com", password="Secret123!", role=UserRole.USER)
    user = await service.register_user(create_cmd)
    assert user["user"]["email"] == "u@test.com"
    user_id = list(repo.saved.keys())[0]

    # delete
    del_cmd = DeleteUserCommand(user_id=user_id, admin_user_id=None)
    await service.delete_user(del_cmd)
    assert user_id not in repo.saved
