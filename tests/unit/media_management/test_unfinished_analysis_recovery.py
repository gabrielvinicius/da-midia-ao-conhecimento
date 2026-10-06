"""Mídias que ficaram "em análise" além do prazo viram falha, com aviso."""
import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.services.unfinished_analysis_recovery import (
    GIVE_UP_MESSAGE,
    UnfinishedAnalysisRecovery,
)
from src.media_management.domain import Media, MediaStatus, MediaType
from src.shared.domain.events import MediaFailed

NOW = datetime.datetime(2026, 1, 1, 12, tzinfo=datetime.timezone.utc)


def _analyzing():
    media = Media.create(
        media_id=uuid4(), user_id=uuid4(), filename="aula.mp4", file_size_bytes=1,
        media_type=MediaType.VIDEO, storage_provider="local", original_file_path="u/a.mp4",
    )
    media.status = MediaStatus.ANALYZING
    return media


@pytest.mark.asyncio
async def test_stuck_analysis_fails_the_media_and_warns_the_owner():
    stuck = _analyzing()
    repo = MagicMock()
    repo.list_analyzing_since_before = AsyncMock(return_value=[stuck])
    repo.update = AsyncMock()
    bus = MagicMock()
    bus.publish = AsyncMock()

    failed = await UnfinishedAnalysisRecovery(repo, bus, give_up_seconds=3 * 3600).sweep(NOW)

    assert failed == [str(stuck.id)]
    assert repo.list_analyzing_since_before.await_args.args[0] == NOW - datetime.timedelta(hours=3)
    assert (stuck.status, stuck.error_message) == (MediaStatus.FAILED, GIVE_UP_MESSAGE)
    event = bus.publish.await_args.args[0]
    assert isinstance(event, MediaFailed) and event.stage == "analysis"


def test_the_deadline_must_be_positive():
    with pytest.raises(ValueError):
        UnfinishedAnalysisRecovery(MagicMock(), MagicMock(), give_up_seconds=0)
