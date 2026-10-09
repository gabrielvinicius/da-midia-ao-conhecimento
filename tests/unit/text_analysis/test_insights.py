"""Revisão de estudo e qualidade da IA, calculadas sobre as análises gravadas."""
import datetime
from uuid import uuid4

import pytest

from src.shared.application.access import Requester
from src.shared.domain.errors import NotFoundError
from src.text_analysis.application.insights import notebook, topic_overview
from src.text_analysis.application.services.analysis_review_service import AnalysisReviewService
from src.text_analysis.domain.entities.sentiment import TextChunk
from src.text_analysis.domain.review import ReviewCard, question_key
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
        FeedbackRecord(corrected.media_id, 1, "Ótimo resumo", now),
        FeedbackRecord(corrected.media_id, -1, None, now - datetime.timedelta(days=1)),
        FeedbackRecord(untouched.media_id, 1, "Faltou um tema", now - datetime.timedelta(days=2)),
    ]

    report = quality_report([corrected, untouched], feedback)

    assert report.analyses == 2
    assert report.corrected == {"resumo": 1, "temas": 0, "capítulos": 0, "perguntas": 0}
    # O polegar grava 1 (útil) ou -1: "útil" não pode virar a pior nota.
    assert (report.useful, report.not_useful, report.useful_share) == (2, 1, 66.7)
    assert [c.comment for c in report.recent_comments] == ["Ótimo resumo", "Faltou um tema"]
    assert [c.media_id for c in report.recent_corrections] == [corrected.media_id]


def test_quality_report_without_ratings_has_no_average():
    assert quality_report([], []).useful_share is None


@pytest.mark.asyncio
async def test_repository_lists_only_the_users_analyses():
    repo = InMemoryAnalysisRepository()
    mine, other = uuid4(), uuid4()
    await repo.save(_analysis(["P"], user_id=mine))
    await repo.save(_analysis(["Q"], user_id=other))

    assert [a.user_id for a in await repo.list_analyses(str(mine))] == [mine]
    assert len(await repo.list_analyses()) == 2


# --- Revisão espaçada, caderno e temas ---------------------------------------

NOW = datetime.datetime(2026, 10, 9, 12, 0, tzinfo=datetime.timezone.utc)


def test_right_answers_space_the_reviews_and_a_wrong_one_starts_over():
    card = ReviewCard()
    for expected_days in (1, 3, 7, 14, 14):
        card = card.answered(True, NOW)
        assert card.due_at == NOW + datetime.timedelta(days=expected_days)
    assert card.box == 5 and card.mastered and card.correct_count == 5

    card = card.answered(False, NOW)
    assert (card.box, card.due_at, card.wrong_count) == (1, NOW, 1)
    assert card.is_due(NOW) and not card.mastered


def test_question_key_ignores_case_accents_and_punctuation():
    assert question_key("O que é a LGPD?") == question_key("o que e a lgpd")


def test_deck_marks_progress_and_what_is_due():
    analysis = _analysis(["Pergunta A", "Pergunta B"])
    learned = ReviewCard().answered(True, NOW)  # volta amanhã
    progress = {(str(analysis.id), question_key("Pergunta A")): learned}

    questions = study_deck([analysis], progress, now=NOW)[0].questions

    assert (questions[0].progress, questions[0].due) == (learned, False)
    assert (questions[1].progress, questions[1].due) == (None, True)


def test_notebook_lists_summaries_with_main_topics():
    with_summary, without = _analysis(), _analysis()
    with_summary.summary = "Resumo da aula"

    entries = notebook([with_summary, without])

    assert [e.analysis_id for e in entries] == [with_summary.id]
    assert entries[0].topics == ["Tema A"] and entries[0].chapters == 1


def test_topics_are_grouped_across_media_by_title():
    first, second = _analysis(), _analysis()
    first.topics = [Topic(id=0, keywords=["dados"], title="Proteção de dados", snippets=["trecho"], chunk_indices=[1])]
    first.chunks = [TextChunk("c0", "a", 0, 10), TextChunk("c1", "b", 42.0, 50)]
    second.topics = [
        Topic(id=0, keywords=["lgpd"], title="proteção de Dados!"),
        Topic(id=1, keywords=["x"], title="Outro tema"),
    ]

    groups = topic_overview([first, second])

    assert [(g.title, g.media_count) for g in groups] == [("Proteção de dados", 2), ("Outro tema", 1)]
    assert groups[0].occurrences[0].start == 42.0 and groups[0].occurrences[0].snippet == "trecho"


class _Progress:
    def __init__(self):
        self.saved = {}

    async def progress_of(self, user_id):
        return {}

    async def card(self, user_id, analysis_id, key):
        return self.saved.get((user_id, analysis_id, key))

    async def save(self, user_id, analysis_id, key, card):
        self.saved[(user_id, analysis_id, key)] = card


@pytest.mark.asyncio
async def test_answering_a_question_moves_it_between_boxes():
    user = uuid4()
    repo, progress = InMemoryAnalysisRepository(), _Progress()
    analysis = _analysis(["O que é DDD?"], user_id=user)
    await repo.save(analysis)
    service = AnalysisReviewService(repo, feedback_repo=None, progress=progress)
    requester = Requester(user_id=user)

    assert (await service.answer_question(analysis.id, requester, "o que é ddd", True)).box == 2
    assert (await service.answer_question(analysis.id, requester, "O que é DDD?", False)).box == 1
    with pytest.raises(NotFoundError):
        await service.answer_question(analysis.id, requester, "Pergunta que não existe", True)
    with pytest.raises(NotFoundError):  # análise de outro usuário
        await service.answer_question(analysis.id, Requester(user_id=uuid4()), "O que é DDD?", True)
