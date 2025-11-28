import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from src.shared.infrastructure.database import Base
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.domain.user import User
from src.notifications.infrastructure.notification_repository import NotificationRepository
from src.notifications.domain.notification import Notification, NotificationType
from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_processing.transcription.domain.transcription import Transcription
from src.media_management.infrastructure.orm.media_entity import MediaEntity
from src.media_management.domain.enums import MediaType

# Configure in-memory SQLite for integration tests with StaticPool to avoid threading issues
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def integration_db_session():
    # Use StaticPool to share the connection across the session and avoid threading errors
    engine = create_async_engine(
        TEST_DB_URL, 
        echo=False, 
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_repository_save_and_find(integration_db_session: AsyncSession):
    repo = UserRepository(integration_db_session)
    user = User.create(email="test@integration.com", password_hash="hash")
    
    # Save
    saved_user = await repo.save(user)
    assert saved_user.id == user.id
    
    # Find by ID
    fetched_user = await repo.find_by_id(user.id)
    assert fetched_user is not None
    assert fetched_user.email == user.email
    
    # Find by Email
    fetched_by_email = await repo.find_by_email("test@integration.com")
    assert fetched_by_email is not None
    assert fetched_by_email.id == user.id

@pytest.mark.asyncio
async def test_notification_repository_save_and_list(integration_db_session: AsyncSession):
    # Need a user first due to FK
    user_repo = UserRepository(integration_db_session)
    user = User.create(email="notify@integration.com", password_hash="hash")
    await user_repo.save(user)
    
    repo = NotificationRepository(integration_db_session)
    notification = Notification(
        user_id=user.id,
        type=NotificationType.EMAIL,
        content="Integration Test"
    )
    
    # Save
    saved_notif = await repo.save(notification)
    assert saved_notif.id == notification.id
    
    # List by User
    user_notifs = await repo.list_by_user(str(user.id))
    assert len(user_notifs) == 1
    assert user_notifs[0].content == "Integration Test"

@pytest.mark.asyncio
async def test_transcription_repository_lifecycle(integration_db_session: AsyncSession):
    # Need user and media due to FKs
    user_repo = UserRepository(integration_db_session)
    user = User.create(email="media@integration.com", password_hash="hash")
    await user_repo.save(user)
    
    # Manually create MediaEntity as MediaRepo is not fully refactored/exposed cleanly yet
    media_id = uuid.uuid4()
    media = MediaEntity(
        id=media_id,
        user_id=user.id,
        original_file_path="/tmp/test.mp3",
        media_type=MediaType.AUDIO,
        storage_provider="local"
    )
    integration_db_session.add(media)
    await integration_db_session.flush()
    
    repo = TranscriptionRepository(integration_db_session)
    transcription = Transcription(media_id=media_id)
    
    # Add
    await repo.add(transcription)
    
    # Get by ID
    fetched = await repo.get_by_id(transcription.id)
    assert fetched is not None
    assert fetched.media_id == media_id
    
    # Update
    fetched.content = "Updated content"
    await repo.update(fetched)
    
    fetched_updated = await repo.get_by_id(transcription.id)
    assert fetched_updated.content == "Updated content"
