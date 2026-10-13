from uuid import uuid4

import pytest

from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.services.text_analysis_service import (
    TextAnalysisService,
)
from src.text_analysis.domain import Document
from src.text_analysis.domain import SentimentLabel, Sentiment, TextChunk, Topic
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import InMemoryAnalysisRepository


class FakeChunker:
    def chunk(self, document: Document, size: int, overlap: int):
        return [TextChunk(id="c1", text=document.text, start=None, end=None)]


class FakeSentiment:
    def analyze(self, chunks, language):
        return [Sentiment(chunk_id=chunks[0].id, label=SentimentLabel.NEUTRAL, score=0.5)]


class FakeEmbeddings:
    def embed(self, texts):
        return [[float(len(texts[0]))]]


class FakeTopics:
    async def model_topics(self, chunks, embeddings, language):
        topic = Topic(id=0, keywords=["test"], snippets=["sample"], size=1, title="Tópico")
        return [topic], {}


class FakeTextGen:
    def is_available(self):
        return True

    async def summarize_topic(self, title, content, keywords, language):
        return f"Summary of {title}"


class InMemoryRepo(InMemoryAnalysisRepository):
    def __init__(self):
        super().__init__()
        self.saved = {}

    async def save(self, analysis):
        self.saved[str(analysis.id)] = analysis
        return str(analysis.id)

    async def get(self, analysis_id):
        return self.saved.get(analysis_id)

    async def get_by_media_id(self, media_id):
        return next((a for a in self.saved.values() if str(a.media_id) == str(media_id)), None)


from src.text_analysis.application.pipeline.base import AnalysisPipeline
from src.text_analysis.application.pipeline.steps import (
    ChunkingStep,
    SentimentStep,
    TopicModelingStep,
)
from src.text_analysis.application.pipeline.synthesis import SynthesisStep

@pytest.mark.anyio
async def test_analyze_text_service_saves_and_returns_dto():
    repo = InMemoryRepo()
    
    config = AnalysisConfig(chunk_size=50, chunk_overlap=0)
    
    # Build pipeline with fakes
    pipeline = AnalysisPipeline(steps=[
        ChunkingStep(FakeChunker(), size=config.chunk_size, overlap=config.chunk_overlap),
        SentimentStep(FakeSentiment(), language="en"),
        TopicModelingStep(FakeTopics(), FakeEmbeddings(), language="en"),
        SynthesisStep(FakeTextGen(), language="en"),
    ])

    service = TextAnalysisService(
        repository=repo,
        pipeline=pipeline,
        config=config,
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
