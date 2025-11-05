# tests/unit/text_processing/test_process_text_handler.py
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

if "fitz" not in sys.modules:  # pragma: no cover - test shim for environments without PyMuPDF
    sys.modules["fitz"] = SimpleNamespace()

from src.media_management.domain.media import Media, MediaStatus, MediaType
from src.shared.events.domain_events import TextContentReady
from src.text_analysis.text_processing.application.commands.process_text_command import (
    ProcessTextCommand,
)
from src.text_analysis.text_processing.application.commands.process_text_command_handler import (
    ProcessTextCommandHandler,
)


@pytest.fixture
def handler_mocks():
    """Sets up mocks for the ProcessTextCommandHandler dependencies."""
    mock_storage_service = AsyncMock()
    return {
        "media_queries": AsyncMock(),
        "media_repository": AsyncMock(),
        "storage_service_factory": MagicMock(return_value=mock_storage_service),
        "event_bus": AsyncMock(),
        "mock_storage_service": mock_storage_service,
    }

@pytest.mark.asyncio
@patch("src.text_analysis.text_processing.application.commands.handlers.fitz")
async def test_process_text_handler_success(mock_fitz, handler_mocks):
    """Tests that the handler correctly extracts text from a PDF and publishes an event."""
    # Arrange
    media_id = str(uuid4())
    user_id = str(uuid4())
    original_path = f"media/{user_id}/{media_id}/document.pdf"
    media = Media(
        id=media_id,
        user_id=user_id,
        original_file_path=original_path,
        media_type=MediaType.TEXT,
        storage_provider="local",
    )

    handler_mocks["media_queries"].get_by_id.return_value = media
    handler_mocks["mock_storage_service"].download.return_value = b"fake_pdf_bytes"

    # Mock the PyMuPDF library
    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = mock_doc
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is the extracted text."
    mock_doc.__iter__.return_value = iter([mock_page])
    mock_fitz.open.return_value = mock_doc

    handler = ProcessTextCommandHandler(**{k: v for k, v in handler_mocks.items() if k != "mock_storage_service"})
    command = ProcessTextCommand(media_id=media_id, file_path=original_path, storage_provider="local")

    # Act
    await handler.handle(command)

    # Assert
    # 1. It downloaded the original PDF file
    handler_mocks["mock_storage_service"].download.assert_awaited_once_with(original_path)

    # 2. It saved transitional states in the repository
    assert handler_mocks["media_repository"].save.await_count == 2
    first_saved = handler_mocks["media_repository"].save.await_args_list[0].args[0]
    second_saved = handler_mocks["media_repository"].save.await_args_list[1].args[0]
    assert first_saved.status == MediaStatus.PROCESSING
    assert second_saved.status == MediaStatus.COMPLETED
    assert media.status == MediaStatus.UPLOADED  # original aggregate remains immutable

    # 3. It published the correct event with the extracted text
    handler_mocks["event_bus"].publish.assert_awaited_once()
    published_event: TextContentReady = handler_mocks["event_bus"].publish.await_args.args[0]
    assert isinstance(published_event, TextContentReady)
    assert published_event.media_id == media_id
    assert published_event.text_content == "This is the extracted text."
