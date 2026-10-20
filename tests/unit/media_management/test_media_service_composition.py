"""A montagem única do MediaService grava no armazenamento escolhido no envio."""
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.media_management.infrastructure.dependencies.builders import build_media_service


class _Storage:
    def __init__(self, provider, calls):
        self.provider, self.calls = provider, calls

    async def upload_file(self, *, source_path, destination, content_type, move=False):
        self.calls.append(self.provider)
        return {"path": destination, "size": 1}


class _Factory:
    def __init__(self):
        self.calls = []

    def create_storage_service(self, provider):
        return _Storage(provider, self.calls)


@pytest.mark.asyncio
async def test_upload_goes_to_the_provider_chosen_by_the_user():
    """A montagem antiga da API gravava sempre no local e registrava o provedor
    escolhido: leituras e exclusões depois procuravam no lugar errado."""
    factory = _Factory()
    service = build_media_service(session=None, storage_factory=factory, event_bus=None)
    command = SimpleNamespace(user_id=uuid4(), filename="aula.mp4", file_path="/tmp/upload.bin", file_size_bytes=1, storage_provider="s3")

    await service.storage_uploader.upload(command, uuid4(), "video/mp4")

    assert factory.calls == ["s3"]


def test_the_service_has_what_the_api_needs():
    service = build_media_service(session=None, storage_factory=_Factory(), event_bus=None)
    assert service.storage_downloader is not None  # reprodução do arquivo
    assert service.data_erasers  # exclusão completa
