"""Tests for the observability-aware SummarizationService (services module)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.text_analysis.summarization.application.services.summarization_service import (
    SummarizationService,
)
from src.text_analysis.summarization.application.services.summary_metrics_service import (
    SummaryMetricsService,
)
from src.text_analysis.summarization.application.services.summary_state_manager_impl import (
    SummaryStateManagerImpl,
)


@pytest.fixture
def summarization_env() -> dict[str, object]:
    provider = AsyncMock()
    validator = MagicMock()
    validator.validate = MagicMock()
    metrics_collector = MagicMock()
    cache = SimpleNamespace(
        get=AsyncMock(return_value=None),
        set=AsyncMock(),
    )

    service = SummarizationService(
        summarizer_provider=provider,
        validator=validator,
        metrics_service=SummaryMetricsService(metrics_collector),
        state_manager=SummaryStateManagerImpl(cache),
    )

    return {
        "service": service,
        "provider": provider,
        "validator": validator,
        "collector": metrics_collector,
        "cache": cache,
    }


@pytest.mark.asyncio
async def test_summarize_records_metrics_and_caches_result(summarization_env: dict[str, object]) -> None:
    service = summarization_env["service"]
    provider = summarization_env["provider"]
    validator = summarization_env["validator"]
    collector = summarization_env["collector"]
    cache = summarization_env["cache"]

    summary_id = uuid4()
    provider.summarize.return_value = "Resumo final"

    result = await service.summarize("Texto válido com conteúdo suficiente.", summary_id=summary_id)

    validator.validate.assert_called_once()
    provider.summarize.assert_awaited_once_with("Texto válido com conteúdo suficiente.")
    cache.get.assert_awaited_once_with(str(summary_id))
    cache.set.assert_awaited_once_with(str(summary_id), "Resumo final")

    collector.record.assert_called_once()
    event_name, payload = collector.record.call_args.args
    assert event_name == "summary_generated"
    assert payload["success"] is True
    assert payload["duration"] >= 0.0
    assert result == "Resumo final"


@pytest.mark.asyncio
async def test_summarize_propagates_failure_and_records_error_metric(
    summarization_env: dict[str, object],
) -> None:
    service = summarization_env["service"]
    provider = summarization_env["provider"]
    collector = summarization_env["collector"]
    cache = summarization_env["cache"]

    provider.summarize.side_effect = RuntimeError("Falha no provedor")

    with pytest.raises(RuntimeError):
        await service.summarize("Texto válido com conteúdo suficiente.", summary_id=uuid4())

    collector.record.assert_called_once()
    _, payload = collector.record.call_args.args
    assert payload["success"] is False
    cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_summarize_uses_cache_without_metrics_when_available(
    summarization_env: dict[str, object],
) -> None:
    service = summarization_env["service"]
    provider = summarization_env["provider"]
    collector = summarization_env["collector"]
    cache = summarization_env["cache"]

    cached_summary = "Resumo em cache"
    cache.get.return_value = cached_summary

    result = await service.summarize("Texto qualquer para cache.", summary_id=uuid4())

    assert result == cached_summary
    provider.summarize.assert_not_called()
    collector.record.assert_not_called()
    cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_summarize_processes_entries_sequentially_with_metrics(
    summarization_env: dict[str, object],
) -> None:
    service = summarization_env["service"]
    provider = summarization_env["provider"]
    validator = summarization_env["validator"]
    collector = summarization_env["collector"]
    cache = summarization_env["cache"]

    summary_ids = [uuid4(), uuid4()]
    provider.summarize.side_effect = ["Resumo A", "Resumo B"]

    texts = {
        summary_ids[0]: "Texto A com conteúdo extenso.",
        summary_ids[1]: "Texto B igualmente detalhado.",
    }

    result = await service.batch_summarize(texts)

    assert result == {
        summary_ids[0]: "Resumo A",
        summary_ids[1]: "Resumo B",
    }
    assert provider.summarize.await_count == len(summary_ids)
    assert validator.validate.call_count == len(summary_ids)
    assert cache.get.await_count == len(summary_ids)
    assert cache.set.await_count == len(summary_ids)
    assert collector.record.call_count == len(summary_ids)
    for call in collector.record.call_args_list:
        event_name, payload = call.args
        assert event_name == "summary_generated"
        assert payload["success"] is True
        assert payload["duration"] >= 0.0
