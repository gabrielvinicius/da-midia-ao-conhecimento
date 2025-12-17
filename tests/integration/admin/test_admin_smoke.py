import pytest

from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_read_service import AdminReadService
from src.admin.application.services.admin_service import AdminService
from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.ports import (
    AdminMediaRepositoryPort,
    AdminUserRepositoryPort,
)
from src.media_management.domain import Media
from src.shared.domain.enums import MediaStatus
from src.user_management.domain import User, UserRole


class InMemoryUserRepo(AdminUserRepositoryPort):
    def __init__(self):
        self.users = {}

    async def find_by_id(self, user_id):
        return self.users.get(user_id)

    async def save(self, user: User):
        self.users[user.id] = user
        return user

    async def delete(self, user_id):
        return bool(self.users.pop(user_id, None))

    async def count_all(self):
        return len(self.users)

    async def count_active(self):
        return sum(1 for u in self.users.values() if u.is_active)


class InMemoryMediaRepo(AdminMediaRepositoryPort):
    def __init__(self):
        self.media = {}

    async def get_by_id(self, media_id):
        return self.media.get(media_id)

    async def update(self, media):
        self.media[media.id] = media
        return media

    async def delete(self, media_id):
        return bool(self.media.pop(media_id, None))

    async def list_paginated(self, page: int, limit: int):
        items = list(self.media.values())
        start = (page - 1) * limit
        end = start + limit
        return items[start:end]

    async def count_all(self):
        return len(self.media)

    async def count_by_status(self, status):
        return sum(1 for m in self.media.values() if m.status == status)

    async def count_by_user(self, user_id):
        return sum(1 for m in self.media.values() if m.user_id == user_id)

    async def count_by_user_and_status(self, user_id, status):
        return sum(
            1
            for m in self.media.values()
            if m.user_id == user_id and m.status == status
        )


class DummyPermission:
    def validate_admin_operation(self, admin_user, target_user_id):
        return None


@pytest.mark.integration
@pytest.mark.anyio
async def test_admin_smoke():
    user_repo = InMemoryUserRepo()
    media_repo = InMemoryMediaRepo()
    audit = AdminAuditService()

    admin_user = User.create(email="admin@test.com", password_hash="x", role=UserRole.ADMIN)
    await user_repo.save(admin_user)

    media = Media.create(
        media_id=admin_user.id,
        user_id=admin_user.id,
        filename="file.txt",
        file_size_bytes=1,
        media_type="text",
        storage_provider="local",
        original_file_path="/tmp/file.txt",
        transcription_provider=None,
        summarization_provider=None,
        sentiment_provider=None,
        topic_modeling_provider=None,
        language="en",
    )
    media.status = MediaStatus.FAILED
    media_repo.media[media.id] = media

    admin_user_svc = AdminUserService(user_repository=user_repo, permission_service=DummyPermission(), audit_service=audit)
    admin_media_svc = AdminMediaService(media_repository=media_repo, permission_service=DummyPermission(), audit_service=audit, media_service=None)  # type: ignore[arg-type]
    admin_read_svc = AdminReadService(user_read_port=user_repo, media_read_port=media_repo)

    admin_svc = AdminService(
        admin_read_service=admin_read_svc,
        audit_service=audit,
        admin_user_service=admin_user_svc,
        admin_media_service=admin_media_svc,
        user_adapter=admin_user_svc,
        media_adapter=admin_media_svc,
    )

    stats = await admin_svc.get_system_stats(None)
    assert "media_total" in stats or "failed_media" in stats
