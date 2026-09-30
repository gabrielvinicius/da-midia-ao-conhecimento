"""O que é gravado da análise precisa voltar igual na leitura."""
import pytest

from src.text_analysis.application.mappers import analysis_to_dto
from src.text_analysis.domain import Analysis, Document
from src.text_analysis.domain.entities.sentiment import Sentiment, SentimentLabel, TextChunk
from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)


class _CapturingSession:
    def __init__(self):
        self.added = None

    async def get(self, *_):
        return None

    def add(self, obj):
        self.added = obj

    async def commit(self):
        pass

    async def flush(self):
        pass

    async def refresh(self, *_):
        pass

    async def merge(self, obj):
        self.added = obj
        return obj


def _analysis():
    a = Analysis.new(Document.from_payload("texto", []))
    a.chunks = [
        TextChunk(id="c1", text="A derivada mede a variação.", start=12.5, end=20.0),
        TextChunk(id="c2", text="Trecho de documento.", start=None, end=None),
    ]
    a.sentiments = [
        Sentiment(chunk_id="c1", label=SentimentLabel.POSITIVE, score=0.9, text="A derivada mede a variação."),
        Sentiment(chunk_id="c2", label=SentimentLabel.NEUTRAL, score=0.8, text="Trecho de documento."),
    ]
    return a


@pytest.mark.asyncio
async def test_sentiment_keeps_text_and_time_after_save_and_load():
    session = _CapturingSession()
    repo = SqlAlchemyAnalysisRepository(session)
    await repo.save(_analysis())
    payload = session.added.payload

    loaded = repo._payload_to_analysis(payload)
    items = analysis_to_dto(loaded).sentiment_items

    assert items[0].text == "A derivada mede a variação."
    assert (items[0].start, items[0].end) == (12.5, 20.0)
    # documento: sem horário, e não "00:00"
    assert items[1].start is None and items[1].end is None


def test_old_analyses_without_chunks_still_show_the_text():
    a = _analysis()
    a.chunks = []
    items = analysis_to_dto(a).sentiment_items
    assert items[0].text == "A derivada mede a variação."
