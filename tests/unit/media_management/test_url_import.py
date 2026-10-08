"""Importação de vídeos por link do YouTube."""
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.media_management.application.dtos import ImportMediaCommand
from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import FetchedMedia
from src.media_management.application.use_cases.import_media_from_url import ImportMediaFromUrl, youtube_video_url
from src.media_management.infrastructure.adapters.youtube_fetcher_adapter import (
    YoutubeFetcherAdapter,
    _friendly,
    _safe_filename,
)
from src.shared.domain.errors import NotFoundError


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtube.com/watch?v=jNQXAC9IVRw&list=PL123&t=42s",
        "https://youtu.be/jNQXAC9IVRw?si=abc",
        "https://m.youtube.com/watch?v=jNQXAC9IVRw",
        "https://www.youtube.com/shorts/jNQXAC9IVRw",
        "https://www.youtube.com/live/jNQXAC9IVRw?feature=share",
        "  http://www.youtube.com/embed/jNQXAC9IVRw ",
    ],
)
def test_youtube_links_become_the_canonical_video_address(url):
    # Listas e tempos saem: só o vídeo é importado.
    assert youtube_video_url(url) == "https://www.youtube.com/watch?v=jNQXAC9IVRw"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/watch?v=curto",
        "https://youtube.com.evil.com/watch?v=jNQXAC9IVRw",
    ],
)
def test_other_addresses_are_refused(url):
    """O servidor não baixa de qualquer endereço (rede interna, arquivos locais)."""
    with pytest.raises(InvalidUploadError):
        youtube_video_url(url)


def _command(url="https://youtu.be/jNQXAC9IVRw"):
    return ImportMediaCommand(user_id=uuid4(), url=url, correlation_id="req-1")


@pytest.mark.asyncio
async def test_the_downloaded_video_goes_through_the_normal_upload():
    seen = {}

    class Fetcher:
        async def fetch(self, url, target_dir):
            path = os.path.join(target_dir, "jNQXAC9IVRw.mp4")
            with open(path, "wb") as fh:
                fh.write(b"x" * 100)
            seen["url"], seen["dir"] = url, target_dir
            return FetchedMedia(path=path, filename="Me at the zoo.mp4", size_bytes=100)

    upload = AsyncMock()
    upload.execute.return_value = "media"
    use_case = ImportMediaFromUrl(Fetcher(), None, upload, enabled=True)

    assert await use_case.execute(_command()) == "media"
    command = upload.execute.call_args.args[0]
    assert seen["url"] == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    assert (command.filename, command.file_size_bytes, command.correlation_id) == ("Me at the zoo.mp4", 100, "req-1")
    assert not os.path.exists(seen["dir"])  # o temporário é apagado


@pytest.mark.asyncio
async def test_disabled_import_or_a_bad_link_never_reach_the_download():
    fetcher, upload = AsyncMock(), AsyncMock()
    with pytest.raises(NotFoundError):
        await ImportMediaFromUrl(fetcher, fetcher, upload, enabled=False).execute(_command())
    with pytest.raises(InvalidUploadError):
        await ImportMediaFromUrl(fetcher, fetcher, upload, enabled=True).execute(_command("ftp://exemplo.com/video.mp4"))
    fetcher.fetch.assert_not_awaited()
    upload.execute.assert_not_awaited()


def test_long_videos_and_live_streams_are_refused_before_downloading():
    adapter = YoutubeFetcherAdapter(max_bytes=500 * 2**20, max_seconds=3600)
    with pytest.raises(InvalidUploadError, match="90 min; o máximo é 60 min"):
        adapter._check({"duration": 5400})
    with pytest.raises(InvalidUploadError, match="ao vivo"):
        adapter._check({"is_live": True})
    adapter._check({"duration": 1800})


def test_titles_become_safe_file_names_and_errors_readable_messages():
    assert _safe_filename('Aula 1: "Derivadas" / parte 2?') == "Aula 1 Derivadas parte 2.mp4"
    assert _safe_filename("") == "video-do-youtube.mp4"
    assert _friendly("ERROR: [youtube] abc: Private video. Sign in") == "O vídeo é privado."
    assert _friendly("algo inesperado") == "Não foi possível baixar o vídeo do YouTube."
