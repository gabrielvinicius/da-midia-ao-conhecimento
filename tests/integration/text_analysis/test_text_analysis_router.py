"""Integration smoke tests for unified text-analysis endpoints."""

from __future__ import annotations

import os
import importlib
import sys
import types
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient


os.environ.setdefault("LIGHTWEIGHT_BOOTSTRAP", "1")
pytestmark = pytest.mark.anyio("asyncio")


def _ensure_notification_stubs() -> None:
    try:
        importlib.import_module("src.notifications")
        importlib.import_module("src.notifications.config")
    except ModuleNotFoundError:
        pass

    try:
        importlib.import_module("src.notifications.config.settings")
    except ModuleNotFoundError:
        module = types.ModuleType("src.notifications.config.settings")

        class _StubSmtpSettings:  # type: ignore[too-few-public-methods]
            def __init__(self) -> None:
                self.smtp_host = "localhost"
                self.smtp_port = 1025
                self.smtp_user = "stub"
                self.smtp_password = "stub"

        module.SmtpSettings = _StubSmtpSettings  # type: ignore[attr-defined]
        sys.modules["src.notifications.config.settings"] = module

    try:
        importlib.import_module("src.notifications.tasks")
    except ModuleNotFoundError:
        sys.modules["src.notifications.tasks"] = types.ModuleType("src.notifications.tasks")

    if "src.notifications.tasks.notification_tasks" not in sys.modules:
        module = types.ModuleType("src.notifications.tasks.notification_tasks")

        class _StubTask:  # type: ignore[too-few-public-methods]
            @staticmethod
            def delay(*args: Any, **kwargs: Any) -> None:  # noqa: D401
                """No-op Celery delay replacement for tests."""

        module.send_notification_task = _StubTask()  # type: ignore[attr-defined]
        sys.modules["src.notifications.tasks.notification_tasks"] = module

    adapters = {
        "sms_adapter": "SmsAdapter",
        "smtp_adapter": "SMTPAdapter",
        "webhook_adapter": "WebhookAdapter",
    }
    for module_name, class_name in adapters.items():
        full_name = f"src.notifications.infrastructure.{module_name}"
        if full_name not in sys.modules:
            module = types.ModuleType(full_name)

            class _StubAdapter:  # type: ignore[too-few-public-methods]
                def __init__(self, *args: Any, **kwargs: Any) -> None:
                    self.args = args
                    self.kwargs = kwargs

            setattr(module, class_name, _StubAdapter)
            sys.modules[full_name] = module


_ensure_notification_stubs()

main_module = importlib.import_module("main")
if getattr(main_module, "text_analysis_router", None) is None:
    router_module = importlib.import_module("src.text_analysis.api.routers")
    main_module.text_analysis_router = router_module.router
    main_module.app.include_router(main_module.text_analysis_router)

app = main_module.app
@asynccontextmanager
async def _lifespan_override(_: Any):
    yield


app.router.lifespan_context = _lifespan_override  # type: ignore[assignment]
from src.shared.infrastructure import cache as cache_module

# Ensure Redis cache doesn't connect during smoke tests
async def _cache_connect_stub(*args: Any, **kwargs: Any) -> None:
    cache_module.cache.is_connected = True


async def _cache_disconnect_stub(*args: Any, **kwargs: Any) -> None:
    cache_module.cache.is_connected = False


cache_module.cache.connect = _cache_connect_stub  # type: ignore[assignment]
cache_module.cache.disconnect = _cache_disconnect_stub  # type: ignore[assignment]
from src.media_management.api.dependencies import get_media_queries
from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.api.dependencies import get_current_user
from src.text_analysis.sentiment_analysis.api.dependencies import (
    SentimentDependencies,
    get_sentiment_dependencies,
)
from src.text_analysis.sentiment_analysis.infrastructure.sentiment_analysis_repository import (
    SentimentAnalysisRepository,
)
from src.text_analysis.sentiment_analysis.application.sentiment_analysis_service import (
    SentimentAnalysisService,
)
from src.text_analysis.summarization.api.dependencies import (
    SummarizationDependencies,
    get_summarization_dependencies,
)
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.summarization.application.summarization_service import (
    SummarizationService,
)
from src.text_analysis.topic_modeling.api.dependencies import (
    TopicModelingDependencies,
    get_topic_modeling_dependencies,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)
from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.user_management.domain.user import User, UserRole

from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.text_analysis.summarization.domain.model.summary_aggregate import SummaryAggregate
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.media_management.domain.media import Media, MediaType

from tests.mocks.in_memory_text_analysis import (
    InMemorySummarizationRepo,
    InMemorySentimentRepo,
    InMemoryTopicRepo,
)



class InMemoryMediaQueries(MediaQueries):  # type: ignore[misc]
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id
        self._records: Dict[UUID, Media] = {}

    async def get_by_id(self, media_id: UUID | str) -> Optional[Media]:
        return self._records.get(UUID(str(media_id)))

    def register(self, media_id: UUID, owner_id: UUID) -> None:
        self._records[media_id] = Media(id=media_id, user_id=owner_id, original_file_path="test.mp4", media_type=MediaType.VIDEO)

from src.user_management.bootstrap import UserManagementModule

@pytest.fixture()
def text_analysis_overrides(auth_module: UserManagementModule):
    print("fixture start")
    user = User(id=uuid4(), email="router@test", password_hash="x", role=UserRole.USER, is_active=True)
    auth_module.user_service.create_user(user.email, user.password_hash)
    media_queries = InMemoryMediaQueries(user.id)

    summarization_repo = InMemorySummarizationRepo()
    sentiment_repo = InMemorySentimentRepo()
    topic_repo = InMemoryTopicRepo()

    summarization_service = StubSummarizationService(
        summarization_repo=summarization_repo,
        summarizer=None,  # type: ignore[arg-type]
        text_analysis_service=None,  # type: ignore[arg-type]
    )
    sentiment_service = StubSentimentService(
        analyzer=None,  # type: ignore[arg-type]
        repository=sentiment_repo,
        text_analysis_service=None,  # type: ignore[arg-type]
        logger=None,
        metrics=None,
    )
    topic_service = StubTopicService(
        topic_modeler=None,  # type: ignore[arg-type]
        topic_modeling_repo=topic_repo,
        text_analysis_service=None,  # type: ignore[arg-type]
        topic_logger=None,
        topic_metrics=None,
    )

    main_module = importlib.import_module("main")
    assert getattr(main_module, "text_analysis_router", None) is not None
    async def _current_user() -> User:
        return user

    print("dependency overrides set")
    app.dependency_overrides[get_current_user] = _current_user
    app.dependency_overrides[get_media_queries] = lambda: media_queries
    app.dependency_overrides[get_summarization_dependencies] = lambda: SummarizationDependencies(
        service=summarization_service,
        repository=summarization_repo,
    )
    app.dependency_overrides[get_sentiment_dependencies] = lambda: SentimentDependencies(
        service=sentiment_service,
        repository=sentiment_repo,
    )
    app.dependency_overrides[get_topic_modeling_dependencies] = lambda: TopicModelingDependencies(
        service=topic_service,
        repository=topic_repo,
    )

    yield media_queries, summarization_repo, sentiment_repo, topic_repo

    app.dependency_overrides.clear()
    print("fixture teardown")


async def test_summary_read_flow(client: AsyncClient, auth_token: str, text_analysis_overrides):
    media_queries, summarization_repo, *_ = text_analysis_overrides
    owner_id = media_queries._user_id
    media_id = uuid4()
    media_queries.register(media_id, owner_id)

    aggregate = SummaryAggregate.create(media_id=media_id, provider="builtin")
    await summarization_repo.add(aggregate)
    stored = await summarization_repo.get_by_id(aggregate.id)
    assert stored is not None

    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get(f"/summaries/{aggregate.id}", headers=headers)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == str(aggregate.id)
    assert payload["media_id"] == str(media_id)


async def test_sentiment_read_and_schedule(client: AsyncClient, auth_token: str, text_analysis_overrides):
    media_queries, _, sentiment_repo, _ = text_analysis_overrides
    owner_id = media_queries._user_id
    media_id = uuid4()
    media_queries.register(media_id, owner_id)

    analysis = SentimentAnalysis(media_id=str(media_id), transcription_id="t-1")
    await sentiment_repo.save(analysis)
    assert await sentiment_repo.get_by_media_id(str(media_id)) is not None

    headers = {"Authorization": f"Bearer {auth_token}"}
    get_response = await client.get(f"/sentiment-analysis/?media_id={media_id}", headers=headers)
    queue_response = await client.post(
        "/sentiment-analysis/analyze",
        data={"transcription_id": "t-1", "provider": "huggingface"},
        headers=headers,
    )

    assert get_response.status_code == 200, get_response.text
    payload = get_response.json()
    assert payload["media_id"] == str(media_id)
    assert queue_response.status_code == 200, queue_response.text
    queued_payload = queue_response.json()
    assert queued_payload["analysis"]["task_id"] is not None
    assert queued_payload["analysis"]["provider"] == "huggingface"


async def test_topic_modeling_read_and_schedule(client: AsyncClient, auth_token: str, text_analysis_overrides):
    media_queries, _, _, topic_repo = text_analysis_overrides
    owner_id = media_queries._user_id
    media_id = uuid4()
    media_queries.register(media_id, owner_id)

    result = TopicModelingResult.create(media_id=media_id, provider="sklearn_lda")
    await topic_repo.add(result)
    assert await topic_repo.get_by_media_id(media_id) is not None

    headers = {"Authorization": f"Bearer {auth_token}"}
    get_response = await client.get(f"/topic-modeling/?media_id={media_id}", headers=headers)
    queue_response = await client.post(
        "/topic-modeling/analyze",
        data={
            "text_content": "Lorem ipsum " * 10,
            "provider": "sklearn_lda",
            "language": "en",
        },
        headers=headers,
    )

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["media_id"] == str(media_id)

    assert queue_response.status_code == 200, queue_response.text
    queue_payload = queue_response.json()
    assert queue_payload["analysis"]["task_id"] is not None
    assert queue_payload["analysis"]["provider"] == "sklearn_lda"
