from uuid import uuid4

import pytest

from src.media_management.application.dtos import (
    CreateMediaCommand,
    DeleteMediaCommand,
    ReprocessMediaCommand,
)
from src.media_management.application.ports import UploadMetadata
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.shared.domain.enums import MediaStatus


class FakeRepo:
    def __init__(self):
        self.saved = {}

    async def save(self, media):
        self.saved[media.id] = media
        return media

    async def get_by_id(self, media_id):
        return self.saved.get(media_id)

    async def delete(self, media_id):
        self.saved.pop(media_id, None)

    async def update(self, media):
        self.saved[media.id] = media

    async def count_all(self): ...
    async def count_by_user(self, user_id): ...
    async def count_by_status(self, status): ...
    async def count_by_user_and_status(self, user_id, status): ...
    async def list_paginated(self, page: int, limit: int): ...


class FakeUploader:
    async def upload(self, command, media_id, content_type: str):
        return type("UploadResult", (), {"destination_path": f"/fake/{media_id}", "metadata": {"size": len(command.file)}})()


class FakeMetadataMapper:
    def map(self, storage_metadata, default_path, file_data: bytes):
        return UploadMetadata(stored_path=default_path, file_size=len(file_data))


class FakeMaintenance:
    def __init__(self):
        self.deleted = []
    async def delete_file(self, provider: str, path: str):
        self.deleted.append((provider, path))


class FakeTranscriptionCleanup:
    def __init__(self):
        self.cleaned = []
    async def delete_by_media_id(self, media_id):
        self.cleaned.append(media_id)


class FakeBus:
    def __init__(self):
        self.events = []
    async def publish(self, event):
        self.events.append(event)


@pytest.mark.integration
@pytest.mark.anyio
async def test_delete_and_reprocess_flow():
    repo = FakeRepo()
    read_service = MediaReadService(media_repository=repo)
    maintenance = FakeMaintenance()
    cleanup = FakeTranscriptionCleanup()
    bus = FakeBus()

    service = MediaService(
        media_repository=repo,
        storage_uploader=FakeUploader(),
        metadata_mapper=FakeMetadataMapper(),
        metrics_service=None,
        upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=read_service,
        event_bus=bus,
        emit_legacy_task=False,
        storage_maintenance=maintenance,
        transcription_cleanup=cleanup,
    )

    cmd = CreateMediaCommand(
        user_id=str(uuid4()),
        file=b"hello",
        filename="file.mp4",
        storage_provider="local",
        transcription_provider=None,
        summarization_provider=None,
        sentiment_provider=None,
        topic_modeling_provider=None,
        metadata=None,
    )
    media = await service.create_media(cmd)

    # mark failed for reprocess
    media.status = MediaStatus.FAILED
    await repo.update(media)
    await service.reprocess_media(ReprocessMediaCommand(media_id=media.id), user_id=media.user_id, user_role=None)

    await service.delete_media(DeleteMediaCommand(media_id=media.id), user_id=media.user_id, user_role=None)

    assert media.id not in repo.saved
    assert maintenance.deleted  # file deletion attempted
    assert cleanup.cleaned == [media.id]
