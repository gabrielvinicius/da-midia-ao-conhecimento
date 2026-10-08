"""Importação por link direto: vídeo, áudio, PDF, documento ou imagem."""
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from src.media_management.application.dtos import ImportMediaCommand
from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import FetchedMedia
from src.media_management.application.use_cases.import_media_from_url import (
    ImportMediaFromUrl,
    direct_link_url,
)
from src.media_management.infrastructure.adapters.direct_link_fetcher_adapter import DirectLinkFetcherAdapter

ALLOWED = ["mp4", "mp3", "wav", "pdf", "docx", "txt", "png", "jpg"]
PUBLIC = {"arquivos.exemplo.org": ["93.184.216.34"], "cdn.exemplo.org": ["93.184.216.35"]}
INTERNAL = {"postgres": ["172.18.0.3"], "localhost": ["127.0.0.1"], "metadata": ["169.254.169.254"]}


def _resolver(host, port):
    addresses = {**PUBLIC, **INTERNAL}.get(host)
    if addresses is None:
        raise OSError("nome não encontrado")
    return addresses


def _adapter(handler, max_bytes=10_000):
    return DirectLinkFetcherAdapter(
        max_bytes=max_bytes, allowed_extensions=ALLOWED, resolver=_resolver, transport=httpx.MockTransport(handler)
    )


def _file(content=b"%PDF-1.4 conteudo", headers=None):
    return lambda request: httpx.Response(200, content=content, headers=headers or {})


@pytest.mark.asyncio
async def test_a_pdf_link_is_saved_with_its_name(tmp_path):
    fetched = await _adapter(_file()).fetch("https://arquivos.exemplo.org/docs/Lei%20Geral.pdf", str(tmp_path))
    assert fetched.filename == "Lei Geral.pdf"
    assert fetched.size_bytes == len(b"%PDF-1.4 conteudo")
    assert open(fetched.path, "rb").read().startswith(b"%PDF")


@pytest.mark.asyncio
async def test_the_name_comes_from_the_header_or_the_content_type(tmp_path):
    named = _file(headers={"content-disposition": "attachment; filename*=UTF-8''Aula%201.mp3"})
    assert (await _adapter(named).fetch("https://arquivos.exemplo.org/download?id=7", str(tmp_path))).filename == "Aula 1.mp3"
    typed = _file(headers={"content-type": "video/mp4"})
    assert (await _adapter(typed).fetch("https://arquivos.exemplo.org/stream/123", str(tmp_path))).filename == "123.mp4"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ["http://postgres:5432/", "http://localhost:8000/admin", "http://metadata/latest/meta-data", "http://10.0.0.5/x.pdf"],
)
async def test_internal_addresses_are_refused(url, tmp_path):
    """O servidor não pode ser usado para acessar a rede interna."""
    handler = AsyncMock(side_effect=AssertionError("não deveria conectar"))
    with pytest.raises(InvalidUploadError, match="não é permitido|não existe"):
        await _adapter(handler).fetch(url, str(tmp_path))


@pytest.mark.asyncio
async def test_a_redirect_to_an_internal_address_is_refused(tmp_path):
    def handler(request):
        if request.url.host == "arquivos.exemplo.org":
            return httpx.Response(302, headers={"location": "http://localhost:6379/"})
        raise AssertionError("seguiu o redirecionamento para a rede interna")

    with pytest.raises(InvalidUploadError, match="não é permitido"):
        await _adapter(handler).fetch("https://arquivos.exemplo.org/a.pdf", str(tmp_path))


@pytest.mark.asyncio
async def test_public_redirects_are_followed(tmp_path):
    def handler(request):
        if request.url.host == "arquivos.exemplo.org":
            return httpx.Response(302, headers={"location": "https://cdn.exemplo.org/real/podcast.mp3"})
        return httpx.Response(200, content=b"ID3 audio")

    fetched = await _adapter(handler).fetch("https://arquivos.exemplo.org/p", str(tmp_path))
    assert fetched.filename == "podcast.mp3"


@pytest.mark.asyncio
async def test_pages_unaccepted_types_and_big_files_are_refused(tmp_path):
    page = _file(b"<html>", {"content-type": "text/html; charset=utf-8"})
    with pytest.raises(InvalidUploadError, match="abre uma página"):
        await _adapter(page).fetch("https://arquivos.exemplo.org/view", str(tmp_path))
    zipped = _file(b"PK", {"content-type": "application/zip"})
    with pytest.raises(InvalidUploadError, match="tipo aceito"):
        await _adapter(zipped).fetch("https://arquivos.exemplo.org/a.zip", str(tmp_path))
    big = _file(b"x" * 20_000)  # sem content-length confiável: corta durante a cópia
    with pytest.raises(InvalidUploadError, match="tamanho máximo"):
        await _adapter(big, max_bytes=10_000).fetch("https://arquivos.exemplo.org/v.mp4", str(tmp_path))
    missing = lambda request: httpx.Response(404)  # noqa: E731
    with pytest.raises(InvalidUploadError, match="não foi encontrado"):
        await _adapter(missing).fetch("https://arquivos.exemplo.org/x.pdf", str(tmp_path))


def test_share_links_become_download_links():
    assert (
        direct_link_url("https://drive.google.com/file/d/1AbC_def-GHIjkl/view?usp=sharing")
        == "https://drive.google.com/uc?export=download&id=1AbC_def-GHIjkl"
    )
    assert direct_link_url("https://www.dropbox.com/s/abc/aula.mp4?dl=0") == "https://www.dropbox.com/s/abc/aula.mp4?dl=1"
    assert direct_link_url("https://exemplo.org/a.pdf#page=2") == "https://exemplo.org/a.pdf"
    for bad in ["ftp://exemplo.org/a.pdf", "https://user:senha@exemplo.org/a.pdf", "exemplo.org/a.pdf"]:
        with pytest.raises(InvalidUploadError):
            direct_link_url(bad)


@pytest.mark.asyncio
async def test_youtube_and_direct_links_go_to_their_fetchers():
    youtube, direct, upload = AsyncMock(), AsyncMock(), AsyncMock()
    for fetcher, name in [(youtube, "Video.mp4"), (direct, "Lei.pdf")]:
        fetcher.fetch.return_value = FetchedMedia(path="/tmp/x", filename=name, size_bytes=10)
    use_case = ImportMediaFromUrl(youtube, direct, upload, enabled=True)

    await use_case.execute(ImportMediaCommand(user_id=uuid4(), url="https://youtu.be/jNQXAC9IVRw"))
    await use_case.execute(ImportMediaCommand(user_id=uuid4(), url="https://arquivos.exemplo.org/Lei.pdf"))

    assert youtube.fetch.await_args.args[0] == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    assert direct.fetch.await_args.args[0] == "https://arquivos.exemplo.org/Lei.pdf"
    assert [c.args[0].filename for c in upload.execute.await_args_list] == ["Video.mp4", "Lei.pdf"]
