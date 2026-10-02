"""Leituras da análise: não encontrado vira NotFoundError (404 na API)."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.shared.domain.errors import NotFoundError
from src.text_analysis.application.dtos import (
    GetAnalysisByMediaIdQuery,
    GetAnalysisQuery,
    ListTopicsQuery,
)
from src.text_analysis.application.services.text_analysis_read_service import (
    TextAnalysisReadService,
)

MODULE = "src.text_analysis.application.services.text_analysis_read_service"


def _service(**returns):
    repo = MagicMock()
    for name in ("get", "get_by_media_id", "list_topics"):
        setattr(repo, name, AsyncMock(return_value=returns.get(name)))
    return TextAnalysisReadService(repo), repo


@pytest.mark.asyncio
async def test_missing_analysis_is_not_found():
    service, _ = _service()
    with pytest.raises(NotFoundError):
        await service.get_analysis(GetAnalysisQuery(analysis_id=uuid4()))


@pytest.mark.asyncio
async def test_found_analysis_is_returned_as_a_dict():
    analysis = object()
    service, repo = _service(get=analysis)
    analysis_id = uuid4()
    with patch(f"{MODULE}.analysis_to_dto") as to_dto:
        to_dto.return_value.to_dict.return_value = {"id": str(analysis_id)}
        assert await service.get_analysis(GetAnalysisQuery(analysis_id=analysis_id)) == {
            "id": str(analysis_id)
        }
    repo.get.assert_awaited_once_with(str(analysis_id))
    to_dto.assert_called_once_with(analysis)


@pytest.mark.asyncio
async def test_media_without_analysis_yields_none():
    service, _ = _service()
    assert await service.get_analysis_by_media_id(GetAnalysisByMediaIdQuery(media_id=uuid4())) is None


@pytest.mark.asyncio
async def test_topics_of_a_missing_analysis_are_not_found():
    service, _ = _service(list_topics=None)
    with pytest.raises(NotFoundError):
        await service.list_topics(ListTopicsQuery(analysis_id=uuid4()))


@pytest.mark.asyncio
async def test_analysis_without_topics_returns_an_empty_list():
    service, _ = _service(list_topics=[])
    assert await service.list_topics(ListTopicsQuery(analysis_id=uuid4())) == []
