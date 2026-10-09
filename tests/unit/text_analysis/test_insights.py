"""Revisão de estudo e qualidade da IA, calculadas sobre as análises gravadas."""
import datetime
from uuid import uuid4

import pytest

from src.text_analysis.application.insights import FeedbackRecord, corrected_parts, quality_report, study_deck
from src.text_analysis.domain import Analysis, Topic
from src.text_analysis.domain.chapters import Chapter, ReviewQuestion
from src.text_analysis.domain.entities.document import Document
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import InMemoryAnalysisRepository


def _analysis(questions=(), user_id=None):
    analysis = Analysis.new(Document.from_payload("texto", []), media_id=uuid4(), user_id=user_id)
    analysis.review_questions = [ReviewQuestion(q, f"resposta {q}", 12.0) for q in questions]
    analysis.chapters = [Chapter(0, 60, "Introdução")]
    analysis.topics = [Topic(id=0, keywords=["a"], title="Tema A")]
    return analysis


def test_study_deck_keeps_only_analyses_with_questions():
    with_questions, without = _analysis(["O que é DDD?"]), _analysis()

    deck = study_deck([with_questions, without])

    assert [entry.analysis_id for entry in deck] == [with_questions.id]
    assert deck[0].questions[0].answer == "resposta O que é DDD?" and deck[0].questions[0].start == 12.0


def test_corrected_parts_follow_the_saved_ai_versions():
    analysis = _analysis(["P1"])
    assert corrected_parts(analysis) == []

    analysis.diagnostics["original_ai_summary"] = "resumo da IA"
    analysis.rename_topic(0, "Tema corrigido")
    analysis.correct_study_aids(analysis.chapters, analysis.review_questions)

    assert corrected_parts(analysis) == ["resumo", "temas", "capítulos", "perguntas"]


def test_quality_report_counts_corrections_and_ratings():
    corrected, untouched = _analysis(), _analysis()
    corrected.diagnostics["original_ai_summary"] = "resumo da IA"
    now = datetime.datetime.now(datetime.timezone.utc)
    feedback = [
        FeedbackRecord(corrected.media_id, 5, "Ótimo resumo", now),
        FeedbackRecord(corrected.media_id, 3, None, now - datetime.timedelta(days=1)),
        FeedbackRecord(untouched.media_id, 4, "Faltou um tema", now - datetime.timedelta(days=2)),
    ]

    report = quality_report([corrected, untouched], feedback)

    assert report.analyses == 2
    assert report.corrected == {"resumo": 1, "temas": 0, "capítulos": 0, "perguntas": 0}
    assert report.ratings == {1: 0, 2: 0, 3: 1, 4: 1, 5: 1} and report.rating_average == 4.0
    assert [c.comment for c in report.recent_comments] == ["Ótimo resumo", "Faltou um tema"]
    assert [c.media_id for c in report.recent_corrections] == [corrected.media_id]


def test_quality_report_without_ratings_has_no_average():
    assert quality_report([], []).rating_average is None


@pytest.mark.asyncio
async def test_repository_lists_only_the_users_analyses():
    repo = InMemoryAnalysisRepository()
    mine, other = uuid4(), uuid4()
    await repo.save(_analysis(["P"], user_id=mine))
    await repo.save(_analysis(["Q"], user_id=other))

    assert [a.user_id for a in await repo.list_analyses(str(mine))] == [mine]
    assert len(await repo.list_analyses()) == 2
