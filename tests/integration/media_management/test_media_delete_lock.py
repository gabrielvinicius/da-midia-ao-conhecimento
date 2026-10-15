"""Exclusão de mídia com uma transcrição sendo gravada ao mesmo tempo (PostgreSQL).

Sem a trava, uma transcrição gravada pelo worker entre a limpeza dos dados
derivados e a exclusão do registro fazia a exclusão falhar com violação de
chave estrangeira (visto na CI, em test_admin_manages_own_media_and_owner_is_reported).
"""
import asyncio
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.infrastructure.persistence.models import MediaEntity
from src.media_management.infrastructure.repositories.media_repository import MediaRepository
from src.media_processing.infrastructure.persistence.models import TranscriptionModel
from src.shared.infrastructure.database.db import Base
from src.user_management.infrastructure.persistence.models import UserModel


@pytest_asyncio.fixture
async def media_database():
    url = os.getenv("TEST_POSTGRES_URL", "")
    if not url:
        pytest.skip("TEST_POSTGRES_URL exige um PostgreSQL de testes")
    schema = "media_lock_test_" + uuid4().hex
    control = create_async_engine(url)
    engine = None
    try:
        async with control.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda connection: Base.metadata.create_all(
                    connection,
                    tables=[UserModel.__table__, MediaEntity.__table__, TranscriptionModel.__table__],
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner, media_id = uuid4(), uuid4()
        async with sessions() as session:
            session.add(UserModel(id=owner, email=f"{owner}@example.com", password_hash="unused-test-hash"))
            await session.flush()
            session.add(
                MediaEntity(
                    id=media_id,
                    user_id=owner,
                    original_file_path="pauta.txt",
                    storage_provider="local",
                    media_type=MediaType.TEXT,
                    status=MediaStatus.PROCESSING,
                )
            )
            await session.commit()
        yield sessions, media_id
    finally:
        if engine is not None:
            await engine.dispose()
        async with control.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await control.dispose()


@pytest.mark.asyncio
async def test_transcription_written_during_deletion_waits_and_the_deletion_succeeds(media_database):
    sessions, media_id = media_database

    async def worker_saves_transcription():
        async with sessions() as session:
            session.add(TranscriptionModel(media_id=media_id, content="Reuniao de pauta."))
            await session.commit()

    async with sessions() as deleting:
        repository = MediaRepository(deleting)
        await repository.lock_for_deletion(media_id)

        # O worker grava a transcrição enquanto a exclusão está em andamento:
        # a chave estrangeira precisa da linha travada, então ele espera.
        worker = asyncio.create_task(worker_saves_transcription())
        await asyncio.sleep(0.5)
        assert not worker.done(), "a gravação deveria esperar a exclusão terminar"

        await deleting.delete(await deleting.get(MediaEntity, media_id))
        await deleting.commit()

    # A mídia saiu; a transcrição atrasada falha (a mídia não existe mais),
    # em vez de a exclusão falhar.
    with pytest.raises(IntegrityError):
        await asyncio.wait_for(worker, timeout=10)
    async with sessions() as session:
        assert await session.get(MediaEntity, media_id) is None
        assert (await session.execute(select(TranscriptionModel))).scalars().all() == []
