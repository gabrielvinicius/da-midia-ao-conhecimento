import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm.attributes import flag_modified

from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.infrastructure.persistence.models import MediaEntity
from src.shared.infrastructure.database.db import Base
from src.text_analysis.domain import Analysis, Document
from src.text_analysis.domain.entities.analysis import AnalysisReviewedError
from src.text_analysis.infrastructure.persistence.models import AnalysisModel
from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from src.user_management.infrastructure.persistence.models import UserModel


@pytest_asyncio.fixture
async def analysis_database():
    url = os.getenv("TEST_POSTGRES_URL", "")
    if not url:
        pytest.skip("TEST_POSTGRES_URL exige um PostgreSQL de testes")
    schema = "analysis_test_" + uuid4().hex
    control = create_async_engine(url)
    engine = None
    try:
        async with control.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(
            url, connect_args={"server_settings": {"search_path": schema}}
        )
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda connection: Base.metadata.create_all(
                    connection,
                    tables=[
                        UserModel.__table__,
                        MediaEntity.__table__,
                        AnalysisModel.__table__,
                    ],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner, media_id = uuid4(), uuid4()
        async with sessions() as session:
            session.add(
                UserModel(
                    id=owner,
                    email=f"{owner}@example.com",
                    password_hash="unused-test-hash",
                )
            )
            await session.flush()
            session.add(
                MediaEntity(
                    id=media_id,
                    user_id=owner,
                    original_file_path="test.mp4",
                    storage_provider="local",
                    media_type=MediaType.VIDEO,
                    status=MediaStatus.ANALYZING,
                )
            )
            await session.commit()
        yield (
            sessions,
            Analysis.new(
                Document.from_payload("texto"), media_id=media_id, user_id=owner
            ),
        )
    finally:
        if engine is not None:
            await engine.dispose()
        async with control.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await control.dispose()


@pytest.mark.asyncio
async def test_only_final_persisted_results_are_visible_to_completion_recovery(
    analysis_database,
):
    sessions, analysis = analysis_database
    async with sessions() as session:
        repository = SqlAlchemyAnalysisRepository(session)
        await repository.save_generated(analysis)
        assert await repository.completed_media_ids({analysis.media_id}) == set()
        analysis.pipeline_completed = True
        await repository.save_generated(analysis)
        assert await repository.completed_media_ids({analysis.media_id, uuid4()}) == {
            analysis.media_id
        }
        assert (await repository.get(str(analysis.id))).pipeline_completed is True


@pytest.mark.asyncio
async def test_a_generated_checkpoint_preserves_a_revision_committed_by_another_session(
    analysis_database,
):
    sessions, analysis = analysis_database
    analysis.summary = "Resumo da IA."
    async with sessions() as writer, sessions() as reviewer:
        repository = SqlAlchemyAnalysisRepository(writer)
        await repository.save_generated(analysis)
        await repository.get(str(analysis.id))
        await SqlAlchemyAnalysisRepository(reviewer).update_summary(
            str(analysis.id), "Resumo revisado."
        )
        analysis.summary = "Nova geração."

        with pytest.raises(AnalysisReviewedError):
            await repository.save_generated(analysis)

        kept = await repository.get(str(analysis.id))
        assert kept.summary == "Resumo revisado."
        assert kept.diagnostics["original_ai_summary"] == "Resumo da IA."


@pytest.mark.asyncio
async def test_a_checkpoint_waits_for_a_concurrent_review_before_checking_protection(
    analysis_database,
):
    sessions, analysis = analysis_database
    analysis.summary = "Resumo da IA."
    async with sessions() as writer, sessions() as reviewer:
        repository = SqlAlchemyAnalysisRepository(writer)
        await repository.save_generated(analysis)
        record = (
            await reviewer.execute(
                select(AnalysisModel)
                .where(AnalysisModel.id == analysis.id)
                .with_for_update()
            )
        ).scalar_one()
        record.payload["diagnostics"]["original_ai_summary"] = record.payload["summary"]
        record.payload["summary"] = "Revisão concorrente."
        flag_modified(record, "payload")
        await reviewer.flush()
        pending = asyncio.create_task(repository.save_generated(analysis))
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), timeout=0.2)
            await reviewer.commit()
            with pytest.raises(AnalysisReviewedError):
                await asyncio.wait_for(pending, timeout=5)
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
        assert (
            await repository.get(str(analysis.id))
        ).summary == "Revisão concorrente."


@pytest.mark.asyncio
async def test_a_legacy_payload_can_be_regenerated_with_the_same_review_guard(
    analysis_database,
):
    sessions, analysis = analysis_database
    async with sessions() as session:
        repository = SqlAlchemyAnalysisRepository(session)
        await repository.save(analysis)
        record = (
            await session.execute(
                select(AnalysisModel).where(AnalysisModel.id == analysis.id)
            )
        ).scalar_one()
        record.payload["schema_version"] = 1
        record.payload["topics"] = ["Tema antigo"]
        flag_modified(record, "payload")
        await session.commit()

        analysis.summary = "Resumo atualizado."
        await repository.save_generated(analysis)

        assert (await repository.get(str(analysis.id))).summary == "Resumo atualizado."


@pytest.mark.asyncio
async def test_recovery_composition_reconciles_a_real_media_with_a_persisted_result(
    analysis_database,
):
    from datetime import timedelta
    from unittest.mock import AsyncMock

    from src.media_management.infrastructure.dependencies.recovery import (
        build_unfinished_analysis_recovery,
    )
    from src.media_management.infrastructure.repositories.media_repository import (
        MediaRepository,
    )
    from src.shared.domain.time.clock import utcnow

    sessions, analysis = analysis_database
    analysis.pipeline_completed = True
    async with sessions() as session:
        await SqlAlchemyAnalysisRepository(session).save_generated(analysis)
        bus = AsyncMock()

        failed = await build_unfinished_analysis_recovery(session, bus).sweep(
            utcnow() + timedelta(days=1)
        )

        assert failed == []
        assert (
            await MediaRepository(session).get_by_id(analysis.media_id)
        ).status == MediaStatus.COMPLETED
        bus.publish.assert_not_awaited()
