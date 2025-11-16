import pytest

from src.shared.events.domain_events import TextContentReady
from src.text_analysis.application.event_handlers import (
    build_text_content_ready_handler,
)


class DummyTextAnalysisService:
    def __init__(self) -> None:
        self.calls = []

    async def schedule_summarization_task(self, **kwargs):
        self.calls.append(("summarization", kwargs))

    async def schedule_sentiment_analysis_task(self, **kwargs):
        self.calls.append(("sentiment", kwargs))

    async def schedule_topic_modeling_task(self, **kwargs):
        self.calls.append(("topic", kwargs))


@pytest.mark.anyio
async def test_text_content_ready_handler_schedules_tasks():
    service = DummyTextAnalysisService()
    handler = build_text_content_ready_handler(service)

    event = TextContentReady(
        media_id="media-1",
        transcription_id="trans-9",
        text_content="Hello world",
        metadata={
            "summarization_provider": "cohere",
            "summarization_options": {"max_length": 20},
            "sentiment_provider": "hf",
            "sentiment_model": "distilbert",
            "language": "en",
            "topic_provider": "lda",
            "topic_options": {"k": 3},
        },
    )

    await handler(event)

    assert ("summarization", {
        "transcription_id": "trans-9",
        "media_id": "media-1",
        "text_content": "Hello world",
        "provider": "cohere",
        "options": {"max_length": 20},
    }) in service.calls

    assert ("sentiment", {
        "transcription_id": "trans-9",
        "text": "Hello world",
        "provider": "hf",
        "model": "distilbert",
        "media_id": "media-1",
        "language": "en",
    }) in service.calls

    assert ("topic", {
        "media_id": "media-1",
        "text_content": "Hello world",
        "provider": "lda",
        "language": "en",
        "options": {"k": 3},
    }) in service.calls


@pytest.mark.anyio
async def test_text_content_ready_handler_skips_without_text():
    service = DummyTextAnalysisService()
    handler = build_text_content_ready_handler(service)

    event = TextContentReady(media_id="media-1", text_content=None)
    await handler(event)

    assert service.calls == []
