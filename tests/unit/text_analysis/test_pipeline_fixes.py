"""Testes das correções do pipeline de análise (segmentos, indexação, visão,
sentimento, títulos dos temas, checkpoints e busca semântica)."""
from uuid import uuid4

import pytest

from src.text_analysis.application.ports import TextGenerationUnavailableError

from src.text_analysis.application.pipeline.base import AnalysisPipeline, AnalysisStep
from src.text_analysis.application.pipeline.steps import (
    KnowledgeIndexingStep,
    SentimentStep,
    TopicTitleStep,
    VisualInsightStep,
)
from src.text_analysis.application.services.knowledge_base_service import (
    KnowledgeBaseService,
)
from src.text_analysis.domain import (
    Analysis,
    Document,
    Sentiment,
    SentimentLabel,
    TextChunk,
    Topic,
)
from src.text_analysis.infrastructure.adapters.chunking_simple_adapter import (
    SimpleChunker,
)
from src.text_analysis.infrastructure.adapters.embeddings_sentence_transformers_adapter import (
    SentenceTransformerEmbeddingAdapter,
)

# --- divisão em trechos -------------------------------------------------------

def test_chunker_groups_segments_and_keeps_timestamps():
    segments = [
        {"text": "Primeira frase.", "start": 0.0, "end": 2.0},
        {"text": "Segunda frase.", "start": 2.0, "end": 4.0},
        {"text": "Terceira frase bem mais longa que as outras.", "start": 4.0, "end": 9.0},
    ]
    chunks = SimpleChunker().chunk(Document.from_payload("", segments), size=35, overlap=0)

    assert [c.text for c in chunks] == [
        "Primeira frase. Segunda frase.",
        "Terceira frase bem mais longa que as outras.",
    ]
    assert (chunks[0].start, chunks[0].end) == (0.0, 4.0)
    assert (chunks[1].start, chunks[1].end) == (4.0, 9.0)


# --- sentimento ---------------------------------------------------------------

@pytest.mark.parametrize(
    "label, expected",
    [
        ("positive", SentimentLabel.POSITIVE),
        ("Negative", SentimentLabel.NEGATIVE),
        ("neutral", SentimentLabel.NEUTRAL),
        ("5 stars", SentimentLabel.POSITIVE),
        ("1 star", SentimentLabel.NEGATIVE),
        ("3 stars", SentimentLabel.NEUTRAL),
        ("LABEL_2", SentimentLabel.POSITIVE),
        ("desconhecido", SentimentLabel.NEUTRAL),
    ],
)
def test_sentiment_label_normalization(label, expected):
    assert SentimentLabel.normalize(label) is expected


class _FixedSentiment:
    def __init__(self, sentiments):
        self._sentiments = sentiments

    def analyze(self, chunks, language):
        return self._sentiments


@pytest.mark.asyncio
async def test_overall_sentiment_is_weighted_by_frequency():
    """Um trecho positivo com confiança alta não pode vencer vários neutros."""
    chunks = [TextChunk(id=str(i), text="t") for i in range(4)]
    sentiments = [Sentiment(chunk_id="0", label=SentimentLabel.POSITIVE, score=0.95)] + [
        Sentiment(chunk_id=str(i), label=SentimentLabel.NEUTRAL, score=0.6) for i in range(1, 4)
    ]
    analysis = Analysis.new(Document.from_payload("t"))
    analysis.chunks = chunks

    await SentimentStep(_FixedSentiment(sentiments), language="pt").process(analysis)

    assert analysis.overall_sentiment is SentimentLabel.NEUTRAL
    assert analysis.diagnostics["sentiment_distribution"] == {
        "positive": 1, "negative": 0, "neutral": 3,
    }


# --- indexação semântica ------------------------------------------------------

class _FakeVectorRepo:
    def __init__(self):
        self.calls = []

    async def save_chunks(self, media_id, chunks, replace=True):
        self.calls.append((media_id, chunks))


@pytest.mark.asyncio
async def test_indexing_saves_chunks_with_embeddings_and_times():
    repo = _FakeVectorRepo()
    media_id = uuid4()
    analysis = Analysis.new(Document.from_payload("t"), media_id=media_id)
    analysis.chunks = [
        TextChunk(id="a", text="trecho a", start=0.0, end=5.0),
        TextChunk(id="b", text="trecho b", start=5.0, end=9.0),
    ]
    analysis.chunk_embeddings = [[0.1, 0.2], [0.3, 0.4]]

    await KnowledgeIndexingStep(repo).process(analysis)

    saved_media, records = repo.calls[0]
    assert saved_media == media_id
    assert records[0]["text"] == "trecho a"
    assert records[0]["embedding"] == [0.1, 0.2]
    assert records[1]["metadata"]["start"] == 5.0
    assert analysis.diagnostics["indexed_chunks"] == 2


@pytest.mark.asyncio
async def test_indexing_without_media_does_nothing():
    repo = _FakeVectorRepo()
    analysis = Analysis.new(Document.from_payload("t"))
    analysis.chunks = [TextChunk(id="a", text="a")]
    analysis.chunk_embeddings = [[0.1]]

    await KnowledgeIndexingStep(repo).process(analysis)

    assert repo.calls == []
    assert analysis.diagnostics["indexed_chunks"] == 0


# --- análise visual -----------------------------------------------------------

def test_frame_timestamps_scale_with_duration():
    assert len(VisualInsightStep.frame_timestamps(60)) == 3       # mínimo
    assert len(VisualInsightStep.frame_timestamps(15 * 60)) == 5  # ~1 a cada 3 min
    assert len(VisualInsightStep.frame_timestamps(3 * 3600)) == 8  # máximo
    ts = VisualInsightStep.frame_timestamps(600)
    assert all(0 < t < 600 for t in ts) and ts == sorted(ts)


class _NeverCalled:
    async def describe_frame(self, *_a, **_k):
        raise AssertionError("não deveria descrever quadros de áudio")

    async def extract_frames(self, *_a, **_k):
        raise AssertionError("não deveria extrair quadros de áudio")

    def get_download_service(self, *_a):
        raise AssertionError("não deveria baixar arquivos de áudio")


@pytest.mark.asyncio
async def test_visual_step_skips_audio_media():
    segments = [{"text": "oi", "start": 0.0, "end": 100.0}]
    analysis = Analysis.new(Document.from_payload("oi", segments), media_id=uuid4())
    analysis.diagnostics.update({"media_type": "AUDIO", "file_path": "a.mp3"})
    never = _NeverCalled()

    await VisualInsightStep(never, never, never).process(analysis)

    assert "visual_context" not in analysis.diagnostics


class _FakeDownloader:
    async def download_file(self, path):
        return b"video"


class _FakeStorage:
    def get_download_service(self, provider):
        return _FakeDownloader()


class _FakeExtractor:
    def __init__(self):
        self.calls = []

    async def extract_frames(self, data, timestamps):
        self.calls.append(len(timestamps))  # o vídeo é gravado uma vez para todos
        return [b"frame"] * len(timestamps)


class _FakeVision:
    def __init__(self):
        self.calls = 0
        self.released = False

    async def describe_frame(self, frame, prompt=""):
        self.calls += 1
        return "Visual description unavailable." if self.calls == 1 else "um slide com um gráfico"

    async def release(self):
        self.released = True


@pytest.mark.asyncio
async def test_visual_step_describes_video_frames_and_skips_failures():
    segments = [{"text": "oi", "start": 0.0, "end": 60.0}]
    analysis = Analysis.new(Document.from_payload("oi", segments), media_id=uuid4())
    analysis.diagnostics.update({"media_type": "VIDEO", "file_path": "v.mp4"})

    vision, extractor = _FakeVision(), _FakeExtractor()
    await VisualInsightStep(vision, extractor, _FakeStorage()).process(analysis)

    context = analysis.diagnostics["visual_context"]
    assert len(context) == 2  # 3 quadros, 1 falhou
    assert all("gráfico" in line for line in context)
    assert context[0].startswith("[00:30]")
    assert extractor.calls == [3]
    assert vision.released  # memória devolvida antes das etapas com o LLM


# --- títulos dos temas --------------------------------------------------------

class _TitleGen:
    def __init__(self, response, unavailable=False):
        self.response = response
        self.unavailable = unavailable
        self.prompt = None

    def is_available(self):
        return True

    async def summarize_topic(self, title, content, keywords, language):
        self.prompt = content
        if self.unavailable:
            raise TextGenerationUnavailableError("nenhum modelo respondeu")
        return self.response


def _topics_analysis():
    analysis = Analysis.new(Document.from_payload("t"))
    analysis.topics = [
        Topic(id=0, title="0_derivada_limite", keywords=["derivada", "limite"], snippets=["s"]),
        Topic(id=1, title="1_integral", keywords=["integral"], snippets=["s"]),
        Topic(id=-1, title="ruído", keywords=[], snippets=["s"]),
    ]
    return analysis


@pytest.mark.asyncio
async def test_topic_titles_are_replaced_by_llm_titles():
    gen = _TitleGen('0: Derivadas e limites\n1: "Integrais definidas"')
    analysis = _topics_analysis()

    await TopicTitleStep(gen, language="pt").process(analysis)

    assert [t.title for t in analysis.topics] == ["Derivadas e limites", "Integrais definidas", "ruído"]
    assert "-1:" not in gen.prompt
    assert analysis.diagnostics["topic_titles_source"] == "llm"


@pytest.mark.asyncio
async def test_topic_titles_kept_when_no_model_answers():
    gen = _TitleGen("", unavailable=True)
    analysis = _topics_analysis()

    await TopicTitleStep(gen, language="pt").process(analysis)

    assert analysis.topics[0].title == "0_derivada_limite"
    assert analysis.diagnostics["topic_titles_source"] == "bertopic"


# --- pipeline: status por etapa e checkpoints ---------------------------------

class _OkStep(AnalysisStep):
    name = "ok_step"

    async def process(self, analysis):
        analysis.summary = "parcial"
        return analysis


class _FailingStep(AnalysisStep):
    name = "failing_step"

    async def process(self, analysis):
        raise RuntimeError("sem memória")


@pytest.mark.asyncio
async def test_pipeline_records_status_and_checkpoints_each_step():
    saved = []

    async def checkpoint(analysis, step_name):
        saved.append((step_name, analysis.summary))

    pipeline = AnalysisPipeline(steps=[_OkStep(), _FailingStep()])
    analysis = await pipeline.run(Analysis.new(Document.from_payload("t")), on_step_completed=checkpoint)

    assert saved == [("ok_step", "parcial"), ("failing_step", "parcial")]
    assert analysis.diagnostics["steps"]["ok_step"] == "ok"
    assert analysis.diagnostics["steps"]["failing_step"].startswith("failed: sem memória")


class _Releasable:
    def __init__(self):
        self.released = 0

    async def release(self):
        self.released += 1


@pytest.mark.asyncio
async def test_pipeline_releases_the_language_model_even_when_a_step_fails():
    llm = _Releasable()
    pipeline = AnalysisPipeline(steps=[_FailingStep()], release_after_run=[llm])
    await pipeline.run(Analysis.new(Document.from_payload("t")))
    assert llm.released == 1


# --- busca semântica ----------------------------------------------------------

def test_e5_prefixes_distinguish_queries_from_passages():
    adapter = SentenceTransformerEmbeddingAdapter("intfloat/multilingual-e5-small", device="cpu")
    assert adapter._with_prefix("regra da cadeia", "query") == "query: regra da cadeia"
    assert adapter._with_prefix("texto", "passage") == "passage: texto"
    other = SentenceTransformerEmbeddingAdapter("outro-modelo", device="cpu")
    assert other._with_prefix("texto", "query") == "texto"


def test_hash_fallback_matches_vector_column_size():
    adapter = SentenceTransformerEmbeddingAdapter("x", device="cpu")
    assert len(adapter._hash_vector("abc")) == 384


class _SyncEmbedder:
    def __init__(self):
        self.kind = None

    def embed(self, texts, kind="passage"):
        self.kind = kind
        return [[0.5, 0.5]]


class _Row:
    media_id = uuid4()
    content = "trecho"
    metadata_json = {"start": 12.0, "end": 20.0}


class _SearchRepo:
    async def semantic_search(self, vector, limit=5, user_id=None):
        assert vector == [0.5, 0.5]
        return [(_Row(), 0.25)]


@pytest.mark.asyncio
async def test_knowledge_search_embeds_query_and_returns_timestamps():
    embedder = _SyncEmbedder()
    results = await KnowledgeBaseService(_SearchRepo(), embedder).search("regra da cadeia")

    assert embedder.kind == "query"
    assert results[0]["relevance"] == 75.0
    assert (results[0]["start"], results[0]["end"]) == (12.0, 20.0)


def test_topic_excerpts_are_the_most_representative_in_time_order():
    from src.text_analysis.infrastructure.adapters.topic_modeling_bertopic_adapter import (
        representative_snippets,
    )

    chunks = [TextChunk(id=str(i), text=f"t{i}") for i in range(8)]
    # 0 e 7 são atípicos; os demais ficam perto do centro do tema
    vectors = [[0, 1]] + [[1, 0.05 * i] for i in range(1, 7)] + [[0, -1]]
    picked = representative_snippets(chunks, list(range(8)), vectors, limit=3)
    # antes: sempre os primeiros, inclusive o atípico t0
    assert picked == ["t2", "t3", "t4"]
    assert representative_snippets(chunks, [0, 7], vectors) == ["t0", "t7"]
