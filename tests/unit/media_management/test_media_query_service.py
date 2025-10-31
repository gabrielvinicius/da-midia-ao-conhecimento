"""Unit tests for MediaQueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.media_management.application.services import MediaQueryService


def _service(media_queries=None, access_policy=None):
    return MediaQueryService(
        media_queries=media_queries or AsyncMock(),
        access_policy=access_policy or MagicMock(),
    )


@pytest.mark.asyncio
async def test_list_media_for_user_delegates_to_queries():
    media_queries = AsyncMock()
    expected = [MagicMock()]
    media_queries.list_all.return_value = expected

    service = _service(media_queries=media_queries)

    result = await service.list_media_for_user(user_id=UUID(int=1))

    media_queries.list_all.assert_awaited_once()
    assert result is expected


@pytest.mark.asyncio
async def test_get_media_for_user_checks_policy():
    media = MagicMock()
    media_queries = AsyncMock()
    media_queries.get_by_id.return_value = media
    access_policy = MagicMock()

    service = _service(media_queries=media_queries, access_policy=access_policy)

    result = await service.get_media_for_user(
        media_id=UUID(int=2),
        user_id=UUID(int=3),
    )

    access_policy.ensure_can_access.assert_called_once()
    assert result is media


@pytest.mark.asyncio
async def test_get_media_for_user_raises_when_policy_blocks():
    media_queries = AsyncMock()
    media_queries.get_by_id.return_value = MagicMock()
    access_policy = MagicMock()
    access_policy.ensure_can_access.side_effect = PermissionError

    service = _service(media_queries=media_queries, access_policy=access_policy)

    with pytest.raises(PermissionError):
        await service.get_media_for_user(media_id=UUID(int=4), user_id=UUID(int=5))


@pytest.mark.asyncio
async def test_get_media_statistics_returns_expected_shape():
    media_queries = AsyncMock()
    media_queries.count_by_user.return_value = 5
    media_queries.count_by_user_and_status.return_value = 2

    service = _service(media_queries=media_queries)

    stats = await service.get_media_statistics(user_id=UUID(int=6))

    assert "total" in stats and "by_status" in stats
