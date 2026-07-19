"""
Test Configuration & Fixtures

Shared pytest fixtures for the Jarvis test suite.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Use an in-memory SQLite database for testing (no PostgreSQL needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a clean database session for each test.

    Creates tables before the test, rolls back after.
    """
    from app.infrastructure.database import Base

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def user_repo(db_session: AsyncSession):
    """Provide a UserRepository with a test session."""
    from app.infrastructure.repositories import UserRepository
    return UserRepository(db_session)


@pytest.fixture
def conversation_repo(db_session: AsyncSession):
    """Provide a ConversationRepository with a test session."""
    from app.infrastructure.repositories import ConversationRepository
    return ConversationRepository(db_session)


@pytest.fixture
def message_repo(db_session: AsyncSession):
    """Provide a MessageRepository with a test session."""
    from app.infrastructure.repositories import MessageRepository
    return MessageRepository(db_session)


@pytest.fixture
def auth_service(user_repo):
    """Provide an AuthService with a test UserRepository."""
    from app.application.services.auth_service import AuthService
    return AuthService(user_repo=user_repo)
