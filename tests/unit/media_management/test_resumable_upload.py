"""Envio em partes: arquivos acima do limite de 100 MB por requisição da Cloudflare."""
import datetime
import os
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.dtos import StartUploadCommand
from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.use_cases.resumable_upload import ResumableUpload
from src.media_management.infrastructure.adapters.disk_upload_staging import DiskUploadStaging
from src.shared.domain.errors import ConflictError, NotFoundError


async def _chunks(*parts: bytes):
    for part in parts:
        yield part


def _use_case(tmp_path, part_max_bytes=10, upload=None):
    upload = upload or MagicMock()
    upload.execute = getattr(upload, "execute", None) or AsyncMock()
    staging = DiskUploadStaging(str(tmp_path))
    return ResumableUpload(staging, upload, part_max_bytes, datetime.timedelta(hours=24)), staging, upload


def _start(user_id, size=25, filename="aula.mp4"):
    return StartUploadCommand(user_id=user_id, filename=filename, size_bytes=size, storage_provider="local")


@pytest.mark.asyncio
async def test_parts_build_the_file_and_completion_becomes_a_normal_upload(tmp_path):
    use_case, staging, upload = _use_case(tmp_path)
    seen = {}

    async def execute(command):
        with open(command.file_path, "rb") as fh:
            seen["content"] = fh.read()
        seen["command"] = command
        return "media"

    upload.execute = AsyncMock(side_effect=execute)
    user = uuid4()
    staged = await use_case.start(_start(user))

    assert await use_case.receive(staged.upload_id, user, 0, _chunks(b"a" * 6, b"b" * 4)) == 10
    assert await use_case.receive(staged.upload_id, user, 10, _chunks(b"c" * 10)) == 20
    assert await use_case.receive(staged.upload_id, user, 20, _chunks(b"d" * 5)) == 25
    assert await use_case.complete(staged.upload_id, user, "req-1") == "media"

    assert seen["content"] == b"a" * 6 + b"b" * 4 + b"c" * 10 + b"d" * 5
    command = seen["command"]
    assert (command.filename, command.file_size_bytes, command.correlation_id) == ("aula.mp4", 25, "req-1")
    assert os.listdir(tmp_path) == []  # a área temporária é limpa


@pytest.mark.asyncio
async def test_a_repeated_part_rewrites_the_same_stretch(tmp_path):
    """Uma parte interrompida é reenviada do mesmo ponto, sem duplicar bytes."""
    use_case, _, _ = _use_case(tmp_path)
    user = uuid4()
    staged = await use_case.start(_start(user, size=15))
    await use_case.receive(staged.upload_id, user, 0, _chunks(b"x" * 10))

    assert await use_case.receive(staged.upload_id, user, 0, _chunks(b"y" * 10)) == 10
    assert (await use_case.status(staged.upload_id, user)).received_bytes == 10


@pytest.mark.asyncio
async def test_a_gap_or_an_oversized_part_is_refused(tmp_path):
    use_case, _, _ = _use_case(tmp_path)
    user = uuid4()
    staged = await use_case.start(_start(user, size=15))

    with pytest.raises(ConflictError):
        await use_case.receive(staged.upload_id, user, 5, _chunks(b"x"))
    with pytest.raises(InvalidUploadError):  # acima da maior parte (10)
        await use_case.receive(staged.upload_id, user, 0, _chunks(b"x" * 11))
    await use_case.receive(staged.upload_id, user, 0, _chunks(b"x" * 10))
    with pytest.raises(InvalidUploadError):  # além do tamanho declarado (15)
        await use_case.receive(staged.upload_id, user, 10, _chunks(b"x" * 6))


@pytest.mark.asyncio
async def test_an_incomplete_upload_does_not_become_a_media(tmp_path):
    use_case, _, upload = _use_case(tmp_path)
    user = uuid4()
    staged = await use_case.start(_start(user))
    await use_case.receive(staged.upload_id, user, 0, _chunks(b"x" * 10))

    with pytest.raises(InvalidUploadError):
        await use_case.complete(staged.upload_id, user, None)
    upload.execute.assert_not_called()


@pytest.mark.asyncio
async def test_another_user_does_not_see_the_upload(tmp_path):
    use_case, _, _ = _use_case(tmp_path)
    staged = await use_case.start(_start(uuid4()))

    with pytest.raises(NotFoundError):
        await use_case.status(staged.upload_id, uuid4())
    with pytest.raises(NotFoundError):
        await use_case.receive(staged.upload_id, uuid4(), 0, _chunks(b"x"))


@pytest.mark.asyncio
async def test_the_file_is_checked_before_any_byte_arrives(tmp_path):
    upload = MagicMock()
    upload.check_request.side_effect = InvalidUploadError("Formato de arquivo não suportado")
    use_case, _, _ = _use_case(tmp_path, upload=upload)

    with pytest.raises(InvalidUploadError):
        await use_case.start(_start(uuid4(), filename="planilha.xlsx"))
    assert not os.path.exists(tmp_path / "x") and os.listdir(tmp_path) == []


@pytest.mark.asyncio
async def test_abandoned_uploads_are_removed_when_a_new_one_starts(tmp_path):
    use_case, staging, _ = _use_case(tmp_path)
    user = uuid4()
    old = await use_case.start(_start(user))
    await staging.remove_created_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1))
    assert await staging.get(old.upload_id) is not None  # ainda no prazo

    removed = await staging.remove_created_before(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1)
    )
    assert removed == 1 and await staging.get(old.upload_id) is None


@pytest.mark.asyncio
async def test_cancel_removes_the_upload(tmp_path):
    use_case, staging, _ = _use_case(tmp_path)
    user = uuid4()
    staged = await use_case.start(_start(user))

    await use_case.cancel(staged.upload_id, user)
    assert await staging.get(staged.upload_id) is None


@pytest.mark.asyncio
async def test_without_staging_the_feature_is_unavailable():
    use_case = ResumableUpload(None, MagicMock(), 10, datetime.timedelta(hours=1))
    with pytest.raises(NotFoundError):
        await use_case.start(_start(uuid4()))
