from src.text_analysis.application.commands.analyze_text import (
    AnalyzeTextCommand,
    AnalyzeTextCommandHandler,
)
from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.domain import Sentiment, SentimentLabel, TextChunk, Topic
from src.text_analysis.infrastructure.repository_inmemory import InMemoryAnalysisRepository
from src.text_analysis.infrastructure.chunking import SimpleChunker


class FakeSentiment:
    def analyze(self, chunks, language):
        return [
            Sentiment(chunk_id=chunk.id, label=SentimentLabel.NEUTRAL, score=0.5)
            for chunk in chunks
        ]


class FakeEmbeddings:
    def embed(self, texts):
        return [[float(len(text))] for text in texts]


class FakeTopics:
    def model_topics(self, chunks, embeddings, language):
        topic = Topic(
            topic_id=0,
            keywords=["teste", "topico"],
            snippets=[chunks[0].text],
            title="Teste",
            size=len(chunks),
            diagnostics={"method": "fake"},
        )
        return [topic], {"method": "fake"}


class FakeLLM:
    def __init__(self):
        self.available = True

    def is_available(self):
        return self.available

    def summarize_topic(self, title_hint, content, keywords, language):
        return "# Sumario\n**Resumo**\n- ok\n**Subtópicos**\n1. **x**\n   - y\n**Termos-chave**\n- t"


def test_analyze_text_command_flow():
    handler = AnalyzeTextCommandHandler(
        sentiment_service=FakeSentiment(),
        embedding_service=FakeEmbeddings(),
        topic_modeling=FakeTopics(),
        text_generation=FakeLLM(),
        chunker=SimpleChunker(),
        repository=InMemoryAnalysisRepository(),
        config=AnalysisConfig(chunk_size=50, chunk_overlap=5),
    )

    dto = handler(AnalyzeTextCommand(text="texto curto para teste"))

    assert dto.analysis_id
    assert dto.overall_sentiment == SentimentLabel.NEUTRAL.value
    assert dto.topics[0].summary_md.startswith("#")

