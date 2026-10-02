"""Armazenamento S3 contra a API do S3 simulada pelo moto.

Antes, a opção "s3" gravava no disco local; este teste confere que os
arquivos vão para o bucket e voltam dele.
"""
import pytest

moto = pytest.importorskip("moto")

from src.storage.domain.value_objects.file_path import FilePath  # noqa: E402
from src.storage.infrastructure.adapters.s3_storage_adapter import S3StorageRepository  # noqa: E402


@pytest.fixture
def repo():
    import boto3

    with moto.mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        yield S3StorageRepository(bucket="midias", client=client), client


@pytest.mark.asyncio
async def test_store_retrieve_and_metadata(repo):
    storage, client = repo
    path = FilePath("u1/2026/10/m1/aula.mp4")

    meta = await storage.store(path, b"conteudo")

    assert meta.size.bytes == 8
    assert client.get_object(Bucket="midias", Key="u1/2026/10/m1/aula.mp4")["Body"].read() == b"conteudo"
    assert await storage.retrieve(path) == b"conteudo"
    assert await storage.exists(path)
    assert (await storage.get_metadata(path)).content_type == "video/mp4"


@pytest.mark.asyncio
async def test_missing_file_is_none_not_an_error(repo):
    storage, _ = repo
    await storage.store(FilePath("u1/a.txt"), b"x")  # cria o bucket
    assert await storage.retrieve(FilePath("u1/nada.txt")) is None
    assert await storage.get_metadata(FilePath("u1/nada.txt")) is None
    assert await storage.remove(FilePath("u1/nada.txt")) is False


@pytest.mark.asyncio
async def test_remove_folder_deletes_only_that_media(repo):
    storage, _ = repo
    for key in ("u1/m1/a.mp4", "u1/m1/b.wav", "u1/m10/c.mp4"):
        await storage.store(FilePath(key), b"x")

    assert await storage.remove_folder("u1/m1") is True
    assert await storage.list_files("u1/") == ["u1/m10/c.mp4"]  # "m10" não é "m1"
    assert await storage.remove_folder("u1/m1") is False
    with pytest.raises(ValueError):
        await storage.remove_folder("../fora")


@pytest.mark.asyncio
async def test_download_goes_straight_to_disk(repo, tmp_path):
    """O worker baixa a mídia direto para o disco, sem lê-la para a memória."""
    storage, _ = repo
    await storage.store(FilePath("u1/aula.mp4"), b"video")
    target = tmp_path / "aula.mp4"

    assert await storage.download_to(FilePath("u1/aula.mp4"), str(target)) is True
    assert target.read_bytes() == b"video"
    assert await storage.download_to(FilePath("u1/nada.mp4"), str(tmp_path / "x")) is False


@pytest.mark.asyncio
async def test_local_download_copies_the_file(tmp_path):
    from src.storage.infrastructure.persistence.local_storage_repository import LocalStorageService

    local = LocalStorageService(tmp_path / "root")
    await local.store(FilePath("u1/a.txt"), b"texto")
    target = tmp_path / "copia.txt"

    assert await local.download_to(FilePath("u1/a.txt"), str(target)) is True
    assert target.read_bytes() == b"texto"
    assert await local.download_to(FilePath("u1/nada.txt"), str(tmp_path / "y")) is False
