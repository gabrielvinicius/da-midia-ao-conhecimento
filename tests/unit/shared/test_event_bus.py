"""O barramento continua entregando eventos depois que um handler falha."""
import asyncio
from dataclasses import dataclass

import pytest

from src.shared.domain.events import DomainEvent
from src.shared.infrastructure.messaging.event_bus import create_inmemory_event_bus


@dataclass
class _Ping(DomainEvent):
    n: int = 0


@pytest.mark.asyncio
async def test_consumer_survives_handler_failure():
    bus = create_inmemory_event_bus()
    seen: list[int] = []

    async def flaky(event: _Ping) -> None:
        if event.n == 1:
            raise ConnectionError("banco fora do ar")
        seen.append(event.n)

    bus.subscribe(_Ping, flaky)
    await bus.start_listener()
    try:
        for n in (1, 2, 3):
            await bus.publish(_Ping(n=n))
        await asyncio.wait_for(bus._publisher._queue.join(), timeout=2)
    finally:
        await bus.stop_listener()

    assert seen == [2, 3]


@pytest.mark.asyncio
async def test_one_failing_handler_does_not_block_the_others():
    bus = create_inmemory_event_bus()
    seen: list[str] = []

    async def broken(event: _Ping) -> None:
        raise RuntimeError("falhou")

    async def healthy(event: _Ping) -> None:
        seen.append("ok")

    bus.subscribe(_Ping, broken)
    bus.subscribe(_Ping, healthy)
    await bus.start_listener()
    try:
        await bus.publish(_Ping(n=1))
        await asyncio.wait_for(bus._publisher._queue.join(), timeout=2)
    finally:
        await bus.stop_listener()

    assert seen == ["ok"]


@pytest.mark.asyncio
async def test_synchronous_dispatch_runs_all_handlers_then_reports_failure():
    bus = create_inmemory_event_bus()
    seen: list[str] = []

    async def broken(event: _Ping) -> None:
        raise RuntimeError("falhou")

    async def healthy(event: _Ping) -> None:
        seen.append("ok")

    bus.subscribe(_Ping, broken)
    bus.subscribe(_Ping, healthy)

    with pytest.raises(RuntimeError):
        await bus.publish(_Ping(n=1))
    assert seen == ["ok"]
