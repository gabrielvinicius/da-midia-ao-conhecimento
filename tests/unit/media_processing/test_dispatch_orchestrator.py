from uuid import UUID, uuid4

import pytest

from src.media_processing.application.dispatch_orchestrator import (
    DispatchAction,
    MediaDispatchOrchestrator,
)
from src.media_processing.application.dispatch_repository import DispatchRecord


class StubRepository:
    def __init__(self):
        self._record = None
        self.failed: list[tuple[UUID, str]] = []

    def mark_processing(self, media_id: UUID):
        return self._record

    def mark_failed(self, media_id: UUID, reason: str) -> None:
        self.failed.append((media_id, reason))


@pytest.mark.asyncio
async def test_prepare_actions_returns_text_pipeline():
    repo = StubRepository()
    media_id = uuid4()
    repo._record = DispatchRecord(
        media_id=media_id,
        file_path="media/file.txt",
        storage_provider="local",
        transcription_provider="fastwhisper",
        language="pt",
        media_type="TEXT",
        file_size_bytes=123,
        summarization_provider="built-in",
        sentiment_provider="huggingface",
        topic_modeling_provider="legacy",
    )

    orchestrator = MediaDispatchOrchestrator(repository=repo)
    actions = orchestrator.prepare_actions(media_id)

    assert actions == [
        DispatchAction(
            name="text_document",
            payload={
                "media_id": str(media_id),
                "file_path": "media/file.txt",
                "storage_provider": "local",
                "extraction_method": "basic",
                "language": "pt",
                "summarization_provider": "built-in",
                "sentiment_provider": "huggingface",
                "topic_modeling_provider": "legacy",
            },
            fatal=True,
        )
    ]


def test_prepare_actions_marks_failure_when_path_missing():
    repo = StubRepository()
    media_id = uuid4()
    repo._record = DispatchRecord(
        media_id=media_id,
        file_path="",
        storage_provider="local",
        transcription_provider="fastwhisper",
        language="en",
        media_type="AUDIO",
        file_size_bytes=None,
        summarization_provider=None,
        sentiment_provider=None,
        topic_modeling_provider=None,
    )

    orchestrator = MediaDispatchOrchestrator(repository=repo)
    actions = orchestrator.prepare_actions(media_id)

    assert actions == []
    assert repo.failed == [(media_id, "missing file path for media")]
