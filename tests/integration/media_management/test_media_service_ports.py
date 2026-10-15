from uuid import uuid4

import pytest

from src.media_management.application.dtos import CreateMediaCommand
from src.media_management.application.ports import (
    MediaMetricsPort,
    MediaRepositoryPort,
    StorageUploaderPort,
    UploadMetadata,
    UploadMetadataMapperPort,
)
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.domain.enums import MediaType


class FakeMediaRepo(MediaRepositoryPort):
    def __init__(self):
        self.saved = {}

    async def save(self, media):
        self.saved[media.id] = media
        return media

    async def get_by_id(self, media_id):
        return self.saved.get(media_id)

    async def lock_for_deletion(self, media_id) -> None:
        pass

    async def delete(self, media_id):
        self.saved.pop(media_id, None)

    async def update(self, media):
        self.saved[media.id] = media

    async def count_all(self):
        return len(self.saved)

    async def count_by_user(self, user_id):
        return sum(1 for m in self.saved.values() if m.user_id == user_id)

    async def count_by_status(self, status):
        return sum(1 for m in self.saved.values() if m.status == status)

    async def count_by_user_and_status(self, user_id, status):
        return sum(1 for m in self.saved.values() if m.user_id == user_id and m.status == status)

    async def list_paginated(self, page: int, limit: int):
        items = list(self.saved.values())
        start = (page - 1) * limit
        return items[start : start + limit]


class FakeUploader(StorageUploaderPort):
    async def upload(self, command, media_id, content_type: str):
        return type("UploadResult", (), {"destination_path": f"/fake/{media_id}", "metadata": {"size": command.file_size_bytes}})()


class FakeMetadataMapper(UploadMetadataMapperPort):
    def map(self, storage_metadata, default_path, file_size: int):
        return UploadMetadata(stored_path=default_path, file_size=file_size)


class FakeMetrics(MediaMetricsPort):
    def __init__(self):
        self.calls = []

    async def record_operation(self, **kwargs):
        self.calls.append(kwargs)
        return None

    def set_context(self, *args, **kwargs):
        return None


class FakeEventBus:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


@pytest.mark.integration
@pytest.mark.anyio
async def test_media_service_create_media_with_ports():
    repo = FakeMediaRepo()
    read_service = MediaReadService(media_repository=repo)
    event_bus = FakeEventBus()
    service = MediaService(
        media_repository=repo,
        storage_uploader=FakeUploader(),
        metadata_mapper=FakeMetadataMapper(),
        metrics_service=FakeMetrics(),
        upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=read_service,
        event_bus=event_bus,
        storage_maintenance=None,
                        storage_downloader=None,
    )

    cmd = CreateMediaCommand(
        user_id=str(uuid4()),
        file_path="/tmp/upload.bin", file_size_bytes=5,
        filename="file.txt",
        storage_provider="local",
        transcription_provider=None,
        metadata=None,
        correlation_id="req-123",
    )

    media = await service.create_media(cmd)

    assert media.id in repo.saved
    assert media.media_type == MediaType.TEXT
    assert repo.saved[media.id].original_file_path.startswith("/fake/")
    # O identificador da requisição segue no evento até as tarefas.
    [event] = event_bus.events
    assert event.media_id == str(media.id)
    assert event.correlation_id == "req-123"
    assert event.file_path == repo.saved[media.id].original_file_path
