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
from src.media_management.domain.enums import MediaStatus


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
        return type("UploadResult", (), {"destination_path": f"/fake/{media_id}", "metadata": {"size": command.file_size_bytes}})()


class FakeMetadataMapper:
    def map(self, storage_metadata, default_path, file_size: int):
        return UploadMetadata(stored_path=default_path, file_size=file_size)


class FakeMaintenance:
    def __init__(self):
        self.deleted = []
    async def delete_file(self, provider: str, path: str):
        self.deleted.append((provider, path))


class FakeEraser:
    def __init__(self, name, log, fail=False):
        self.name = name
        self.log = log
        self.fail = fail
    async def erase(self, media_id):
        if self.fail:
            raise ConnectionError("banco indisponível")
        self.log.append((self.name, media_id))


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
    erased = []
    bus = FakeBus()

    service = MediaService(
        media_repository=repo,
        storage_uploader=FakeUploader(),
        metadata_mapper=FakeMetadataMapper(),
        metrics_service=None,
        upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=read_service,
        event_bus=bus,
        storage_maintenance=maintenance,
        data_erasers=[FakeEraser("text_analysis", erased), FakeEraser("transcription", erased)],
        storage_downloader=None,
    )

    cmd = CreateMediaCommand(
        user_id=str(uuid4()),
        file_path="/tmp/upload.bin", file_size_bytes=5,
        filename="file.mp4",
        storage_provider="local",
        transcription_provider=None,
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
    # O reprocessamento limpa os resultados anteriores e a exclusão limpa de
    # novo, cada módulo os próprios dados, na ordem registrada.
    assert erased == [
        ("text_analysis", media.id),
        ("transcription", media.id),
    ] * 2


@pytest.mark.integration
@pytest.mark.anyio
async def test_delete_stops_when_a_module_cannot_erase_its_data():
    """Antes, a falha virava um aviso no log e a mídia sumia com dados para trás."""
    from src.media_management.application.errors import MediaDataErasureError

    repo = FakeRepo()
    maintenance = FakeMaintenance()
    erased = []
    bus = FakeBus()
    service = MediaService(
        media_repository=repo,
        storage_uploader=FakeUploader(),
        metadata_mapper=FakeMetadataMapper(),
        metrics_service=None,
        upload_validator=MediaUploadValidator(settings=media_settings),
        media_read_service=MediaReadService(media_repository=repo),
        event_bus=bus,
        storage_maintenance=maintenance,
        data_erasers=[FakeEraser("text_analysis", erased, fail=True), FakeEraser("transcription", erased)],
    )
    media = await service.create_media(
        CreateMediaCommand(
            user_id=str(uuid4()),
            file_path="/tmp/upload.bin", file_size_bytes=5,
            filename="file.mp4",
            storage_provider="local",
            transcription_provider=None,
            metadata=None,
        )
    )

    with pytest.raises(MediaDataErasureError):
        await service.delete_media(DeleteMediaCommand(media_id=media.id), user_id=media.user_id, user_role=None)

    # A mídia e o arquivo continuam, e a exclusão pode ser repetida.
    assert media.id in repo.saved
    assert not maintenance.deleted
    assert erased == []
    assert not any(type(e).__name__ == "MediaDeleted" for e in bus.events)
