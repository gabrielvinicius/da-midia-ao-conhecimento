from src.text_analysis.application.commands.analyze_text import AnalyzeTextCommand, AnalyzeTextCommandHandler
from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.domain import Sentiment, SentimentLabel, Topic
from src.text_analysis.infrastructure.chunking import SimpleChunker
from src.text_analysis.infrastructure.repository_inmemory import InMemoryAnalysisRepository


class FakeSentiment:
    def analyze(self, chunks, language):
        return [Sentiment(chunk_id=c.id, label=SentimentLabel.NEUTRAL, score=0.5) for c in chunks]


class FakeEmbeddings:
    def embed(self, texts):
        return [[0.1] for _ in texts]


class FakeTopics:
    def model_topics(self, chunks, embeddings, language):
        topic = Topic(topic_id=0, keywords=["fallback"], snippets=[chunks[0].text], title=None, size=1, diagnostics={})
        return [topic], {}


class OfflineLLM:
    def is_available(self):
        return False

    def summarize_topic(self, *args, **kwargs):
        raise RuntimeError("offline")


def test_fallback_llm_generates_summary():
    handler = AnalyzeTextCommandHandler(
        sentiment_service=FakeSentiment(),
        embedding_service=FakeEmbeddings(),
        topic_modeling=FakeTopics(),
        text_generation=OfflineLLM(),
        chunker=SimpleChunker(),
        repository=InMemoryAnalysisRepository(),
        config=AnalysisConfig(chunk_size=20, chunk_overlap=5),
    )

    dto = handler(AnalyzeTextCommand(text="fallback summary precisa funcionar"))
    assert dto.topics[0].summary_md
    assert "Resumo" in dto.topics[0].summary_md

