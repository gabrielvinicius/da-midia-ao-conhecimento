"""Ações do admin sobre mídias: pelas regras do módulo de mídias, com auditoria."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.admin.application.services.admin_media_service import AdminMediaService
from src.shared.domain.errors import NotFoundError


def _service(failed_ids=(), status="failed"):
    media = MagicMock()
    media.status_of = AsyncMock(return_value=status)
    media.reprocess_media = AsyncMock()
    media.delete_media = AsyncMock()
    media.failed_media_ids = AsyncMock(side_effect=lambda limit: list(failed_ids)[:limit])
    audit = MagicMock()
    audit.log_admin_action = AsyncMock()
    return AdminMediaService(media=media, permission_service=MagicMock(), audit_service=audit), media, audit


@pytest.mark.asyncio
async def test_bulk_reprocess_takes_one_bounded_batch():
    ids = [uuid4() for _ in range(5)]
    service, media, _ = _service(ids)

    result = await service.bulk_reprocess_failed_media(MagicMock(id=uuid4()), limit=3)

    assert [c.args[0] for c in media.reprocess_media.await_args_list] == ids[:3]
    assert (result.reprocessed, result.failed, result.more_pending) == (3, 0, True)


@pytest.mark.asyncio
async def test_one_failing_item_does_not_stop_the_batch():
    service, media, audit = _service([uuid4(), uuid4()])
    media.reprocess_media.side_effect = [RuntimeError("fila fora"), None]

    result = await service.bulk_reprocess_failed_media(MagicMock(id=uuid4()), limit=10)

    assert (result.reprocessed, result.failed, result.more_pending) == (1, 1, False)
    assert audit.log_admin_action.await_args.kwargs["details"] == {"reprocessed_count": 1, "failed_count": 1}


@pytest.mark.asyncio
async def test_actions_on_missing_media_are_refused_without_audit():
    service, media, audit = _service(status=None)

    with pytest.raises(NotFoundError):
        await service.delete_media(uuid4(), MagicMock(id=uuid4()))
    media.delete_media.assert_not_awaited()
    audit.log_admin_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_reprocess_goes_through_the_media_module_and_is_audited():
    service, media, audit = _service(status="failed")
    admin, media_id = MagicMock(id=uuid4()), uuid4()

    await service.reprocess_media(media_id, admin)

    media.reprocess_media.assert_awaited_once_with(media_id, actor_id=admin.id)
    assert audit.log_admin_action.await_args.kwargs["details"] == {"media_status": "failed"}
