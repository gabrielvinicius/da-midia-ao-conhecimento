"""Conclusão do envio em partes com o disco real: o arquivo é movido da área
temporária para o armazenamento, e volta se a mídia não puder ser registrada."""
import datetime
import os
from uuid import uuid4

import pytest

from src.media_management.application.dtos import StartUploadCommand
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.application.use_cases.resumable_upload import ResumableUpload
from src.media_management.application.use_cases.upload_media import UploadMedia
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.disk_upload_staging import DiskUploadStaging
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultUploadMetadataMapper,
    StorageServiceFactoryUploader,
)
from src.storage.application.services.storage_service import StorageService
from src.storage.infrastructure.dependencies.providers import StorageClientAdapter
from src.storage.infrastructure.persistence.local_storage_repository import LocalStorageService
from tests.integration.media_management.test_media_service_ports import FakeMediaRepo

CONTENT = b"a" * 10 + b"b" * 10 + b"c" * 5


class _LocalFactory:
    def __init__(self, root):
        self._storage = StorageClientAdapter(StorageService(LocalStorageService(root)), "local")

    def create_storage_service(self, provider):
        return self._storage


class _RepoDownOnce(FakeMediaRepo):
    def __init__(self):
        super().__init__()
        self.down = True

    async def save(self, media):
        if self.down:
            self.down = False
            raise ConnectionError("banco fora do ar")
        return await super().save(media)


def _stored_files(root):
    return sorted(
        os.path.relpath(os.path.join(folder, name), root)
        for folder, _, names in os.walk(root)
        for name in names
        if ".envios-em-partes" not in folder
    )


async def _staged_upload(root, repo):
    staging = DiskUploadStaging(str(root / ".envios-em-partes"))
    upload = UploadMedia(
        media_repository=repo,
        storage_uploader=StorageServiceFactoryUploader(_LocalFactory(root)),
        metadata_mapper=DefaultUploadMetadataMapper(),
        upload_validator=MediaUploadValidator(settings=media_settings),
    )
    use_case = ResumableUpload(staging, upload, 10, datetime.timedelta(hours=24))
    user = uuid4()
    staged = await use_case.start(
        StartUploadCommand(user_id=user, filename="aula.mp3", size_bytes=len(CONTENT), storage_provider="local")
    )

    async def _part(data):
        yield data

    for offset in range(0, len(CONTENT), 10):
        await use_case.receive(staged.upload_id, user, offset, _part(CONTENT[offset:offset + 10]))
    return use_case, staging, staged.upload_id, user


@pytest.mark.asyncio
async def test_completion_moves_the_staged_file_into_the_storage(tmp_path):
    use_case, staging, upload_id, user = await _staged_upload(tmp_path, FakeMediaRepo())
    staged_path = staging.file_path(upload_id)

    media = await use_case.complete(upload_id, user, None)

    assert not os.path.exists(staged_path)
    assert (tmp_path / media.original_file_path).read_bytes() == CONTENT
    assert os.listdir(tmp_path / ".envios-em-partes") == []


@pytest.mark.asyncio
async def test_a_failed_registration_puts_the_file_back_and_completion_can_be_repeated(tmp_path):
    """Movido o arquivo, a falha do registro o apagaria do armazenamento e da
    área temporária: o usuário teria de enviar os 500 MB de novo."""
    use_case, staging, upload_id, user = await _staged_upload(tmp_path, _RepoDownOnce())

    with pytest.raises(ConnectionError):
        await use_case.complete(upload_id, user, None)

    with open(staging.file_path(upload_id), "rb") as fh:
        assert fh.read() == CONTENT
    assert _stored_files(tmp_path) == []

    media = await use_case.complete(upload_id, user, None)
    assert (tmp_path / media.original_file_path).read_bytes() == CONTENT
