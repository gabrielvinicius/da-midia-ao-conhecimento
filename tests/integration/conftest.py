# tests/integration/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.shared.infrastructure.database import Base
from src.shared.config.database_settings import DatabaseSettings

# Load test database settings
# Make sure your .env.test points to a separate test database
settings = DatabaseSettings()

# Create a new engine for the test database
engine = create_async_engine(settings.database_url, echo=False)

# Create a new sessionmaker for the test database
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Fixture to set up the database before tests and tear it down after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database) -> AsyncSession:
    """Yields a new database session for each test, and rolls back transactions."""
    async with TestingSessionLocal() as session:
        await session.begin_nested()
        yield session
        await session.rollback()
