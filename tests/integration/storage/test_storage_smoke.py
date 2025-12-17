import pytest

from uuid import uuid4
from datetime import datetime, timezone

from src.storage.application.services.storage_service import StorageService
from src.storage.application.ports import StorageRepositoryPort
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_size import FileSize


class InMemoryStorageRepo(StorageRepositoryPort):
    def __init__(self):
        self.files = {}

    async def store(self, path: FilePath, content: bytes) -> FileMetadata:
        self.files[str(path)] = content
        return FileMetadata(
            id=uuid4(),
            file_path=path,
            size=FileSize(len(content)),
            content_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def retrieve(self, path: FilePath):
        return self.files.get(str(path))

    async def remove(self, path: FilePath) -> bool:
        return self.files.pop(str(path), None) is not None

    async def exists(self, path: FilePath) -> bool:
        return str(path) in self.files

    async def get_metadata(self, path: FilePath):
        if str(path) not in self.files:
            return None
        return FileMetadata(
            id=uuid4(),
            file_path=path,
            size=FileSize(len(self.files[str(path)])),
            content_type="text/plain",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def list_files(self, prefix: str = ""):
        return [k for k in self.files if k.startswith(prefix)]


@pytest.mark.integration
@pytest.mark.anyio
async def test_storage_service_smoke():
    repo = InMemoryStorageRepo()
    svc = StorageService(repository=repo)

    path = "tmp/hello.txt"
    await svc.store_file(path, b"hello")
    assert await svc.file_exists(path)
    assert await svc.retrieve_file(path) == b"hello"
    meta = await svc.get_file_metadata(path)
    assert meta is not None and int(meta.size.bytes) == 5
    files = await svc.list_files("tmp/")
    assert path in files
    await svc.delete_file(path)
    assert not await svc.file_exists(path)
