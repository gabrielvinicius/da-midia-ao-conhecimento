"""Uma sessão longa (como a dos workers) relê o que outro processo mudou.

Com expire_on_commit=False, um select que encontra um objeto já carregado
devolvia a cópia em memória. Os repositórios contornavam isso com um rollback
antes de cada leitura ("garante conexão livre"), que também descartava o que
estivesse pendente na sessão.
"""
import asyncio
import uuid

from tests.e2e.test_api_flow import client  # noqa: F401 (sobe a aplicação e o banco)


def test_long_lived_session_sees_changes_committed_elsewhere(client):  # noqa: F811
    from src.media_management.domain import Media
    from src.media_management.domain.enums import MediaStatus, MediaType
    from src.media_management.infrastructure.repositories.media_repository import MediaRepository
    from src.media_processing.domain import Transcription, TranscriptionStatus
    from src.media_processing.infrastructure.repositories.transcription_repository import (
        TranscriptionRepository,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal
    from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import UserRepository
    from src.user_management.domain.entities.user import User
    from src.shared.domain.roles import UserRole

    async def scenario():
        async with AsyncSessionLocal() as setup:
            user = await UserRepository(setup).save(
                User.create(email=f"fresh-{uuid.uuid4().hex[:8]}@teste.com", password_hash="x", role=UserRole.USER)
            )
            media = Media.create(
                media_id=uuid.uuid4(), user_id=user.id, filename="a.mp4", file_size_bytes=1,
                media_type=MediaType.VIDEO, storage_provider="local", original_file_path="u/a.mp4",
            )
            await MediaRepository(setup).add(media)
            transcription = Transcription(media_id=media.id)
            await TranscriptionRepository(setup).save(transcription)

        async with AsyncSessionLocal() as worker, AsyncSessionLocal() as other:
            media_repo, transcription_repo = MediaRepository(worker), TranscriptionRepository(worker)
            assert (await media_repo.get_by_id(media.id)).status == MediaStatus.UPLOADED
            assert (await transcription_repo.get_by_id(transcription.id)).status == TranscriptionStatus.PENDING

            # Outro processo muda os dois registros.
            stopped = await MediaRepository(other).get_by_id(media.id)
            stopped.mark_as_failed("parou")
            await MediaRepository(other).save(stopped)
            changed = await TranscriptionRepository(other).get_by_id(transcription.id)
            changed.mark_as_failed("parou")
            await TranscriptionRepository(other).save(changed)

            assert (await media_repo.get_by_id(media.id)).status == MediaStatus.FAILED
            assert (await transcription_repo.get_by_id(transcription.id)).status == TranscriptionStatus.FAILED

    asyncio.run(scenario())


def test_a_failed_write_does_not_break_the_next_read(client):  # noqa: F811
    from src.media_management.infrastructure.repositories.media_repository import MediaRepository
    from src.notifications.domain import Notification, NotificationType
    from src.notifications.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from src.shared.infrastructure.database.db import AsyncSessionLocal

    async def scenario():
        async with AsyncSessionLocal() as session:
            # Aviso de um usuário inexistente: a chave estrangeira recusa.
            with __import__("pytest").raises(Exception):
                await NotificationRepository(session).save(
                    Notification(user_id=uuid.uuid4(), type=NotificationType.WEBSOCKET, content="x")
                )
            # A mesma sessão continua utilizável.
            assert await MediaRepository(session).get_by_id(uuid.uuid4()) is None

    asyncio.run(scenario())
