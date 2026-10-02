"""Envio desfeito quando a mídia não é gravada; auditoria só no log."""
from uuid import uuid4

import pytest

from src.admin.application.services.admin_audit_service import AdminAuditService
from src.media_management.application.dtos import CreateMediaCommand
from src.media_management.application.ports import UploadMetadata
from src.media_management.application.services.media_read_service import MediaReadService
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from tests.integration.media_management.test_media_service_ports import FakeMediaRepo


class BrokenRepo(FakeMediaRepo):
    async def save(self, media):
        raise ConnectionError("banco fora do ar")


class Uploader:
    def __init__(self):
        self.discarded = []

    async def upload(self, command, media_id, content_type):
        return type("UploadResult", (), {"destination_path": f"u/{media_id}/a.txt", "metadata": {}})()

    async def discard(self, command, destination_path):
        self.discarded.append(destination_path)


class Mapper:
    def map(self, storage_metadata, default_path, file_size):
        return UploadMetadata(stored_path=default_path, file_size=file_size)


@pytest.mark.asyncio
async def test_the_file_is_removed_when_the_media_cannot_be_saved():
    """Era a única origem de arquivos órfãos no armazenamento."""
    repo, uploader = BrokenRepo(), Uploader()
    service = MediaService(
        media_repository=repo, storage_uploader=uploader, metadata_mapper=Mapper(),
        metrics_service=None, upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=MediaReadService(media_repository=repo), event_bus=None,
        storage_maintenance=None, storage_downloader=None,
    )
    command = CreateMediaCommand(user_id=str(uuid4()), file_path="/tmp/upload.bin", file_size_bytes=5, filename="a.txt", storage_provider="local")

    with pytest.raises(ConnectionError):
        await service.create_media(command)

    [path] = uploader.discarded
    assert path.endswith("/a.txt")


@pytest.mark.asyncio
async def test_audit_is_a_log_line_and_keeps_nothing_in_memory():
    audit = AdminAuditService()
    admin = type("Admin", (), {"id": uuid4()})()
    await audit.log_admin_action(admin, "delete_user", "user", uuid4(), details={"target_id": "x"})
    assert not hasattr(audit, "audit_entries")
