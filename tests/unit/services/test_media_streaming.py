"""O reprodutor recebe o vídeo em partes, sem a API carregá-lo inteiro."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.dtos import GetMediaStreamQuery
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.use_cases.stream_media import (
    CHUNK_BYTES,
    StreamMedia,
    content_disposition,
)
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaType


class Storage:
    def __init__(self, size):
        self._size, self.reads = size, []

    async def size(self, provider, path):
        return self._size

    async def read_range(self, provider, path, start, end):
        self.reads.append((start, end))
        return b"x" * (end - start + 1)


def _use_case(storage, filename="aula.mp4"):
    media = Media.create(
        media_id=uuid4(), user_id=uuid4(), filename=filename, file_size_bytes=1,
        original_file_path="u/aula.mp4", media_type=MediaType.VIDEO, storage_provider="local",
    )
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=media)
    return StreamMedia(repo, MediaAccessPolicy(), storage), media


@pytest.mark.asyncio
async def test_open_ended_range_is_read_in_one_megabyte_parts():
    storage = Storage(size=3 * CHUNK_BYTES + 10)
    use_case, media = _use_case(storage)

    dto = await use_case.execute(GetMediaStreamQuery(media_id=media.id, range_header="bytes=0-"), user_id=media.user_id)

    assert storage.reads == []  # nada lido antes de a resposta ser enviada
    total = sum([len(c) async for c in dto.chunks])
    assert total == 3 * CHUNK_BYTES + 10
    assert max(end - start + 1 for start, end in storage.reads) == CHUNK_BYTES
    assert dto.status_code == 206 and dto.headers["Content-Length"] == str(total)


def test_filename_with_quotes_and_accents_does_not_break_the_header():
    header = content_disposition('Aula "final" de cálculo.mp4')
    assert header.startswith('inline; filename="Aula _final_ de c_lculo.mp4"')
    assert "filename*=UTF-8''Aula%20%22final%22%20de%20c%C3%A1lculo.mp4" in header


@pytest.mark.asyncio
async def test_upload_is_staged_on_disk_and_refused_above_the_limit():
    import io
    import os

    from fastapi import UploadFile

    from src.media_management.api.routes import received_file
    from src.media_management.application.errors import InvalidUploadError

    async with received_file(UploadFile(io.BytesIO(b"x" * 10), filename="a.txt"), max_bytes=100) as (path, size):
        assert size == 10 and os.path.getsize(path) == 10 and path.endswith(".txt")
    assert not os.path.exists(path)  # temporário apagado

    with pytest.raises(InvalidUploadError):
        async with received_file(UploadFile(io.BytesIO(b"x" * 101), filename="b.txt"), max_bytes=100):
            pass
