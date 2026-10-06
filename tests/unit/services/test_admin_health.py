"""Alertas do painel: falhas recentes e fila longa, em português."""
from datetime import timedelta

import pytest

from src.admin.application.services.admin_read_service import AdminReadService
from src.media_management.domain.enums import MediaStatus
from src.shared.domain.time.clock import utcnow


class Media:
    def __init__(self, failed_recent=0, failed_old=0, processing=0, waiting=0):
        self.values = (failed_recent, failed_old, processing, waiting)
        self.since = None

    async def count_by_status(self, status, since=None):
        failed_recent, failed_old, processing, waiting = self.values
        if status == MediaStatus.FAILED:
            self.since = since
            return failed_recent if since else failed_recent + failed_old
        return processing if status == MediaStatus.PROCESSING else waiting


class Users:
    async def count_all(self):
        return 10

    async def count_active(self):
        return 2


@pytest.mark.asyncio
async def test_old_failures_no_longer_keep_the_alert_on():
    media = Media(failed_recent=1, failed_old=40)
    health = await AdminReadService(Users(), media).get_system_health_status()

    assert health["status"] == "healthy" and health["issues"] == []
    assert health["failed_media"] == 1
    assert utcnow() - media.since == pytest.approx(timedelta(hours=24), abs=timedelta(seconds=5))


@pytest.mark.asyncio
async def test_recent_failures_and_a_long_queue_raise_alerts_in_portuguese():
    health = await AdminReadService(Users(), Media(failed_recent=6, processing=5, waiting=15)).get_system_health_status()

    assert health["status"] == "warning"
    assert any("falharam nas últimas 24 horas" in i for i in health["issues"])
    assert any("fila está longa" in i for i in health["issues"])
    # Contas desativadas não são "baixa atividade".
    assert not any("activity" in i or "atividade" in i for i in health["issues"])
