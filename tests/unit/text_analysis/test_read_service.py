"""Leituras da análise: inexistente ou de outro usuário viram 404."""
from uuid import uuid4

import pytest

from src.shared.domain.errors import NotFoundError
from src.shared.domain.roles import UserRole
from src.text_analysis.application.access import Requester
from src.text_analysis.application.dtos import (
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
    ListTopicsQuery,
)
from src.text_analysis.application.services.text_analysis_read_service import TextAnalysisReadService
from src.text_analysis.domain import Analysis, Document, Topic
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)

OWNER = Requester(uuid4(), UserRole.USER)
OTHER = Requester(uuid4(), UserRole.USER)
ADMIN = Requester(uuid4(), UserRole.ADMIN)


async def _service(user_id=OWNER.user_id, topics=()):
    repo = InMemoryAnalysisRepository()
    analysis = Analysis.new(Document.from_payload("x"), media_id=uuid4(), user_id=user_id)
    analysis.topics = list(topics)
    await repo.save(analysis)
    return TextAnalysisReadService(repo), analysis


@pytest.mark.asyncio
async def test_owner_and_admin_read_the_analysis():
    service, analysis = await _service()
    for requester in (OWNER, ADMIN):
        result = await service.get_analysis(GetAnalysisQuery(analysis_id=analysis.id), requester)
        assert result["analysis_id"] == str(analysis.id)
    by_media = await service.get_analysis_by_media_id(GetAnalysisByMediaIdQuery(media_id=analysis.media_id), OWNER)
    assert by_media["analysis_id"] == str(analysis.id)


@pytest.mark.asyncio
async def test_missing_or_foreign_analysis_is_not_found():
    service, analysis = await _service()
    with pytest.raises(NotFoundError):
        await service.get_analysis(GetAnalysisQuery(analysis_id=uuid4()), OWNER)
    with pytest.raises(NotFoundError):
        await service.get_analysis(GetAnalysisQuery(analysis_id=analysis.id), OTHER)
    with pytest.raises(NotFoundError):
        await service.get_analysis_by_media_id(GetAnalysisByMediaIdQuery(media_id=uuid4()), OWNER)


@pytest.mark.asyncio
async def test_analysis_without_owner_is_only_for_admins():
    """Antes, uma análise sem dono registrado ficava visível a qualquer um."""
    service, analysis = await _service(user_id=None)
    with pytest.raises(NotFoundError):
        await service.get_analysis(GetAnalysisQuery(analysis_id=analysis.id), OWNER)
    assert await service.get_analysis(GetAnalysisQuery(analysis_id=analysis.id), ADMIN)


@pytest.mark.asyncio
async def test_topics_come_as_dtos():
    service, analysis = await _service(topics=[Topic(id=0, keywords=["limite"], title="Limites")])
    [topic] = await service.list_topics(ListTopicsQuery(analysis_id=analysis.id), OWNER)
    assert topic["title"] == "Limites" and topic["keywords"] == ["limite"]
