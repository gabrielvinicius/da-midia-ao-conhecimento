import pytest

from uuid import uuid4

from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.domain import Sentiment, SentimentLabel, TextChunk, Topic
from src.text_analysis.application.services.text_analysis_service import (
    TextAnalysisService,
)
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)
from src.text_analysis.application.metrics import NoOpTextAnalysisMetrics
from src.text_analysis.application.ports import (
    SentimentServicePort,
    TopicModelingPort,
    TextGenerationPort,
    ChunkingServicePort,
    EmbeddingServicePort,
)


class DummySentiment(SentimentServicePort):
    async def analyze(self, text, language=None):
        # text comes as list of chunks; map to sentiments
        items = []
        for idx, chunk in enumerate(text if isinstance(text, list) else [text]):
            items.append(
                Sentiment(
                    chunk_id=str(idx),
                    label=SentimentLabel.NEUTRAL,
                    score=0.0,
                )
            )
        return items


class DummyTopic(TopicModelingPort):
    async def infer_topics(self, document_id, text):
        return {"topics": []}

    async def model_topics(self, chunks, embeddings, language=None):
        return [Topic(id=0, keywords=["hello", "world"], snippets=["hello world"])], {}


class DummyTextGen(TextGenerationPort):
    async def summarize(self, text, language=None):
        return "summary"

    async def summarize_topic(
        self,
        title_hint: str | None,
        content: str,
        keywords: list[str],
        language: str,
    ) -> str:
        return "summary"

    def is_available(self) -> bool:
        return True


class DummyChunker(ChunkingServicePort):
    def chunk(self, document, size=500, overlap=50):
        return [TextChunk.from_text(document.text)]


class DummyEmbeddings(EmbeddingServicePort):
    async def embed(self, texts):
        return [[0.0] * len(texts)]


class AsyncInMemoryRepo(InMemoryAnalysisRepository):
    async def save(self, analysis):
        return await super().save(analysis)

    async def get(self, analysis_id: str):
        return super().get(analysis_id)

    async def get_by_media_id(self, media_id: str):
        return super().get_by_media_id(media_id)

    async def list_topics(self, analysis_id: str):
        return super().list_topics(analysis_id)


@pytest.mark.integration
@pytest.mark.anyio
async def test_text_analysis_smoke():
    repo = AsyncInMemoryRepo()
    service = TextAnalysisService(
        sentiment_service=DummySentiment(),
        embedding_service=DummyEmbeddings(),
        topic_modeling=DummyTopic(),
        text_generation=DummyTextGen(),
        chunker=DummyChunker(),
        repository=repo,
        config=None,
        metrics=NoOpTextAnalysisMetrics(),
        event_bus=None,
        transcription_queries=None,
        text_analysis_read_service=None,
        settings=None,
    )

    cmd = AnalyzeTextCommand(
        media_id=uuid4(),
        document_id=uuid4(),
        text_content="hello world",
        user_id=None,
    )

    result = await service.analyze_text_content(cmd)
    assert "overall_sentiment" in result
    assert "topics" in result
