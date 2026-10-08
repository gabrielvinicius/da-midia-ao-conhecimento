"""Revisão humana de temas, capítulos e perguntas: a versão da IA fica
guardada, e só o dono (ou um administrador) altera."""
from uuid import uuid4

import pytest

from src.shared.application.access import Requester
from src.shared.domain.errors import NotFoundError, ValidationError
from src.text_analysis.application.mappers import analysis_diagnostics, analysis_to_dto
from src.text_analysis.application.services.analysis_review_service import AnalysisReviewService
from src.text_analysis.domain import Analysis, Document, TextChunk, Topic
from src.text_analysis.domain.chapters import Chapter, ReviewQuestion
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import InMemoryAnalysisRepository
from src.user_management.domain import UserRole

OWNER = Requester(uuid4(), UserRole.USER)
OTHER = Requester(uuid4(), UserRole.USER)


def _analysis():
    analysis = Analysis.new(Document.from_payload("t", []), user_id=OWNER.user_id)
    analysis.chunks = [TextChunk(id=str(i), text=f"t{i}", start=i * 60.0, end=(i + 1) * 60.0) for i in range(4)]
    analysis.topics = [Topic(id=0, keywords=["a"], title="0_crise_ia", chunk_indices=[2, 3])]
    analysis.chapters = [Chapter(0.0, 120.0, "Parte 1"), Chapter(120.0, 240.0, "Parte 2")]
    analysis.review_questions = [ReviewQuestion("Quem?", "Ele.", 0.0)]
    return analysis


async def _service(analysis):
    repo = InMemoryAnalysisRepository()
    await repo.save(analysis)
    return AnalysisReviewService(repo, feedback_repo=None), repo


@pytest.mark.asyncio
async def test_topic_titles_keep_the_ai_title_and_topics_carry_their_start():
    analysis = _analysis()
    service, repo = await _service(analysis)

    await service.rename_topic(analysis.id, OWNER, 0, " A crise e a IA ")
    await service.rename_topic(analysis.id, OWNER, 0, "Crise e IA")

    topic = analysis_to_dto(await repo.get(str(analysis.id))).topics[0]
    assert (topic.title, topic.original_title, topic.start) == ("Crise e IA", "0_crise_ia", 120.0)
    with pytest.raises(NotFoundError):
        await service.rename_topic(analysis.id, OWNER, 7, "x")
    with pytest.raises(NotFoundError):  # 404 para quem não é dono
        await service.rename_topic(analysis.id, OTHER, 0, "x")


@pytest.mark.asyncio
async def test_chapters_and_questions_are_replaced_and_the_ai_version_is_kept_once():
    analysis = _analysis()
    service, _ = await _service(analysis)

    await service.correct_study_aids(
        analysis.id,
        OWNER,
        [Chapter(120.0, 240.0, "Depois"), Chapter(0.0, 120.0, "Começo")],
        [ReviewQuestion("Quem escreveu?", "Dijkstra.", 60.0), ReviewQuestion("Quando?", "1970.", None)],
    )
    await service.correct_study_aids(analysis.id, OWNER, [Chapter(0.0, 240.0, "Tudo")], [])

    data = analysis_diagnostics(analysis)
    assert data["chapters"] == [{"start": 0.0, "end": 240.0, "title": "Tudo"}]
    assert "review_questions" not in data  # todas removidas
    assert [c["title"] for c in data["original_ai_chapters"]] == ["Parte 1", "Parte 2"]
    assert data["original_ai_review_questions"] == [{"question": "Quem?", "answer": "Ele.", "start": 0.0}]


@pytest.mark.asyncio
async def test_empty_titles_or_answers_are_refused():
    analysis = _analysis()
    service, _ = await _service(analysis)
    with pytest.raises(ValidationError):
        await service.correct_study_aids(analysis.id, OWNER, [Chapter(0.0, 60.0, " ")], [])
    with pytest.raises(ValidationError):
        await service.correct_study_aids(analysis.id, OWNER, [], [ReviewQuestion("Por quê?", "", None)])
    with pytest.raises(ValidationError):
        await service.correct_study_aids(analysis.id, OWNER, [Chapter(60.0, 10.0, "Volta")], [])
    assert [c.title for c in analysis.chapters] == ["Parte 1", "Parte 2"]
