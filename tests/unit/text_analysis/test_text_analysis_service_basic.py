from uuid import uuid4

import pytest

from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.services.text_analysis_read_service import (
    TextAnalysisReadService,
)
from src.text_analysis.application.services.text_analysis_service import (
    TextAnalysisService,
)
from src.text_analysis.domain import Document
from src.text_analysis.domain import SentimentLabel, Sentiment, TextChunk, Topic


class FakeChunker:
    def chunk(self, document: Document, size: int, overlap: int):
        return [TextChunk(id="c1", text=document.text, start=None, end=None)]


class FakeSentiment:
    async def analyze(self, chunks, language):
        return [Sentiment(chunk_id=chunks[0].id, label=SentimentLabel.NEUTRAL, score=0.5)]


class FakeEmbeddings:
    async def embed(self, texts):
        return [[float(len(texts[0]))]]


class FakeTopics:
    async def model_topics(self, chunks, embeddings, language):
        topic = Topic(id=0, keywords=["test"], summary="summary", diagnostics={}, snippets=["sample"], size=1, title="Tópico")
        return [topic], {}


class FakeTextGen:
    def is_available(self):
        return True

    async def summarize_topic(self, title, content, keywords, language):
        return f"Summary of {title}"


class InMemoryRepo:
    def __init__(self):
        self.saved = {}

    async def save(self, analysis):
        self.saved[str(analysis.id)] = analysis
        return str(analysis.id)

    async def get(self, analysis_id):
        return self.saved.get(analysis_id)


@pytest.mark.anyio
async def test_analyze_text_service_saves_and_returns_dto():
    repo = InMemoryRepo()
    read_service = TextAnalysisReadService(repository=repo)
    service = TextAnalysisService(
        sentiment_service=FakeSentiment(),
        embedding_service=FakeEmbeddings(),
        topic_modeling=FakeTopics(),
        text_generation=FakeTextGen(),
        chunker=FakeChunker(),
        repository=repo,
        config=AnalysisConfig(chunk_size=50, chunk_overlap=0),
        text_analysis_read_service=read_service,
    )

    command = AnalyzeTextCommand(
        media_id=uuid4(),
        document_id=uuid4(),
        text_content="hello world",
        language="en",
        user_id=uuid4(),
    )

    dto = await service.analyze_text_content(command)

    assert dto["document_id"]
    assert dto["overall_sentiment"] == SentimentLabel.NEUTRAL.value
    assert dto["topics"][0]["keywords"] == ["test"]
    # Ensure it was saved
    assert len(repo.saved) == 1
