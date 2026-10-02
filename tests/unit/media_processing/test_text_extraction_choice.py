"""Escolha do método de extração conforme o tipo do arquivo."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)


def _service(native_text: str = "", ocr_text: str = "texto do OCR"):
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value=native_text)
    ocr = MagicMock()
    ocr.extract = AsyncMock(return_value=ocr_text)
    service = TextExtractionService(
        repository=MagicMock(),
        task_scheduler=None,
        storage_service=MagicMock(),
        text_extractor=extractor,
        ocr_provider=ocr,
    )
    return service, extractor, ocr


@pytest.mark.asyncio
async def test_plain_text_is_read_directly():
    service, _, ocr = _service(native_text="conteúdo")
    assert await service._extract("a.md", "text/markdown", ".md") == ("conteúdo", "text_extractor")
    ocr.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_image_goes_to_ocr():
    service, extractor, _ = _service()
    assert await service._extract("a.png", "image/png", ".png") == ("texto do OCR", "ocr")
    extractor.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_pdf_with_text_keeps_native_text():
    native = "Um PDF com texto selecionável, longo o bastante para dispensar o OCR."
    service, _, ocr = _service(native_text=native)
    assert await service._extract("a.pdf", "application/pdf", ".pdf") == (native, "pdf_native")
    ocr.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_scanned_pdf_falls_back_to_ocr():
    service, _, ocr = _service(native_text="  \n ")
    assert await service._extract("a.pdf", "application/pdf", ".pdf") == ("texto do OCR", "ocr_pdf")
    ocr.extract.assert_awaited_once_with("a.pdf")


@pytest.mark.asyncio
async def test_unknown_type_yields_nothing():
    service, _, _ = _service()
    assert await service._extract("a.bin", "application/octet-stream", ".bin") == ("", "fallback")
