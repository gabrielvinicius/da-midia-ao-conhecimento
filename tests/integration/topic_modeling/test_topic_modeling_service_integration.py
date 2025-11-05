# tests/integration/topic_modeling/test_topic_modeling_service_integration.py
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain.media import Media, MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.text_analysis.topic_modeling.application.topic_modeling_service import (
    TopicModelingService,
)
from src.text_analysis.topic_modeling.domain.topic_modeling import (
    TopicModelingResult,
    TopicModelingStatus,
)
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    InMemoryTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)


class _StubTopicModeler:
    async def model_topics(self, text_content: str, language: str, options=None):
        return {
            "topics": [
                {"id": 0, "name": "Tech", "keywords": ["ai", "ml"], "score": 0.9}
            ],
            "num_topics": 1,
            "language": language,
            "options": options or {},
        }


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analyze_topics_persists_result(db_session: AsyncSession):
    media_repo = MediaRepository(db=db_session)
    media_id = uuid4()
    user_id = uuid4()

    media = Media(
        id=media_id,
        user_id=user_id,
        original_file_path="sample/path.txt",
        media_type=MediaType.TEXT,
        storage_provider="local",
    )
    await media_repo.add(media)

    topic_repo = TopicModelingRepository(db=db_session)

    service = TopicModelingService(
        topic_modeler=_StubTopicModeler(),
        topic_modeling_repo=topic_repo,
        text_analysis_service=AsyncMock(),
        topic_logger=StructuredTopicModelingLogger(),
        topic_metrics=InMemoryTopicModelingMetrics(),
    )

    result = await service.analyze_topics(
        media_id=media_id,
        text_content="This is some text content that contains enough data for modeling.",
        provider="stub",
        language="en",
    )

    assert isinstance(result, TopicModelingResult)
    assert result.status == TopicModelingStatus.COMPLETED
    assert result.media_id == media_id
    assert result.topics

    stored = await db_session.execute(
        select(TopicModelingResult).where(TopicModelingResult.media_id == media_id)
    )
    persisted = stored.scalar_one_or_none()

    assert persisted is not None
    assert persisted.id == result.id
    assert persisted.status == TopicModelingStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_topic_modeling_result_returns_saved_result(db_session: AsyncSession):
    media_repo = MediaRepository(db=db_session)
    media_id = uuid4()
    user_id = uuid4()

    media = Media(
        id=media_id,
        user_id=user_id,
        original_file_path="sample/path.txt",
        media_type=MediaType.TEXT,
        storage_provider="local",
    )
    await media_repo.add(media)

    topic_repo = TopicModelingRepository(db=db_session)

    service = TopicModelingService(
        topic_modeler=_StubTopicModeler(),
        topic_modeling_repo=topic_repo,
        text_analysis_service=AsyncMock(),
        topic_logger=StructuredTopicModelingLogger(),
        topic_metrics=InMemoryTopicModelingMetrics(),
    )

    await service.analyze_topics(
        media_id=media_id,
        text_content="Another chunk of text used for analysis.",
        provider="stub",
        language="en",
    )

    fetched = await service.get_topic_modeling_result(media_id)

    assert fetched is not None
    assert fetched.media_id == media_id
    assert fetched.status == TopicModelingStatus.COMPLETED
