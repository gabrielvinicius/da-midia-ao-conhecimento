"""Fila de processamento no painel do administrador."""
import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.admin.application.services.admin_queue_service import AdminQueueService
from src.media_management.application.dtos import PaginatedMedia
from src.media_management.domain.enums import MediaStatus, MediaType
from src.shared.domain.time.clock import utcnow


def _media(status, minutes_in_stage, user_id, created_minutes_ago=300, name="aula.mp4"):
    now = utcnow()
    return SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        filename=name,
        media_type=MediaType.VIDEO,
        status=status,
        created_at=now - datetime.timedelta(minutes=created_minutes_ago),
        updated_at=now - datetime.timedelta(minutes=minutes_in_stage),
    )


class Media:
    def __init__(self, items, total=None):
        self.items, self.total, self.queries = items, total, []

    async def list_media(self, query):
        self.queries.append(query)
        return PaginatedMedia(items=self.items, total=self.total or len(self.items), page=1, pages=1, limit=query.limit)


class Users:
    def __init__(self, emails):
        self.emails, self.lookups = emails, 0

    async def get_user_by_id(self, query):
        self.lookups += 1
        email = self.emails.get(query.user_id)
        return SimpleNamespace(email=email) if email else None


class Broker:
    async def waiting_tasks(self):
        return {"transcription_queue": 2, "text_analysis_queue": 0}


@pytest.mark.asyncio
async def test_lists_media_in_progress_oldest_first_with_owner_and_stage_time():
    ana, bia = uuid4(), uuid4()
    items = [
        _media(MediaStatus.ANALYZING, 5, ana),
        _media(MediaStatus.PROCESSING, 30, bia),
        _media(MediaStatus.UPLOADED, 2, ana),
    ]
    media, users = Media(items), Users({ana: "ana@x.com", bia: "bia@x.com"})

    snapshot = await AdminQueueService(media, users, Broker()).snapshot()

    query = media.queries[0]
    assert query.order == "asc" and set(query.status) == {
        MediaStatus.UPLOADED, MediaStatus.PROCESSING, MediaStatus.ANALYZING
    }
    assert [i.position for i in snapshot.items] == [1, 2, 3]
    assert [i.owner_email for i in snapshot.items] == ["ana@x.com", "bia@x.com", "ana@x.com"]
    assert users.lookups == 2  # cada dono uma vez
    assert 29 * 60 < snapshot.items[1].stage_seconds < 31 * 60
    assert snapshot.counts == {"uploaded": 1, "processing": 1, "analyzing": 1}
    assert snapshot.broker == {"transcription_queue": 2, "text_analysis_queue": 0}
    assert not any(i.stuck for i in snapshot.items)


@pytest.mark.asyncio
async def test_flags_media_that_stopped_moving():
    owner = uuid4()
    items = [
        _media(MediaStatus.UPLOADED, 40, owner),  # ninguém pegou em 40 min
        _media(MediaStatus.PROCESSING, 60, owner),  # transcrição de 1 h: normal
        _media(MediaStatus.ANALYZING, 200, owner),  # análise parada
    ]

    snapshot = await AdminQueueService(Media(items), Users({})).snapshot()

    assert [i.stuck for i in snapshot.items] == [True, False, True]
    assert snapshot.broker is None  # sem broker, a lista aparece mesmo assim


@pytest.mark.asyncio
async def test_says_when_the_list_was_cut():
    owner = uuid4()
    snapshot = await AdminQueueService(Media([_media(MediaStatus.UPLOADED, 1, owner)], total=150), Users({}), limit=1).snapshot()
    assert snapshot.truncated
