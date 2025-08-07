import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from models.base import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL."""
    # Use in-memory SQLite for tests with JSON support
    return "sqlite+aiosqlite:///:memory:?check_same_thread=false"


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_database_url: str):
    """Create test database engine."""
    engine = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=StaticPool,
    )
    
    # Create tables without JSONB columns for testing
    async with engine.begin() as conn:
        # Create simplified tables for testing
        await conn.run_sync(lambda sync_conn: sync_conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id BIGINT PRIMARY KEY,
                chat_type VARCHAR(20) NOT NULL,
                title VARCHAR(255),
                username VARCHAR(100),
                is_verified BOOLEAN,
                is_scam BOOLEAN,
                is_fake BOOLEAN,
                member_count INTEGER,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await conn.run_sync(lambda sync_conn: sync_conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username VARCHAR(100),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                is_verified BOOLEAN,
                is_scam BOOLEAN,
                is_fake BOOLEAN,
                is_bot BOOLEAN,
                is_premium BOOLEAN,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await conn.run_sync(lambda sync_conn: sync_conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id BIGINT,
                chat_id BIGINT,
                sender_id BIGINT,
                date TIMESTAMP NOT NULL,
                message_type VARCHAR(50) NOT NULL,
                is_read BOOLEAN,
                is_deleted BOOLEAN,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (message_id, chat_id)
            )
        """))
        
        await conn.run_sync(lambda sync_conn: sync_conn.execute("""
            CREATE TABLE IF NOT EXISTS messages_enriched (
                chat_id BIGINT,
                message_id BIGINT,
                context TEXT,
                meaning TEXT,
                embeddings TEXT,
                PRIMARY KEY (chat_id, message_id)
            )
        """))
        
        await conn.run_sync(lambda sync_conn: sync_conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_configs (
                chat_id BIGINT PRIMARY KEY,
                save_messages BOOLEAN NOT NULL,
                enrich_messages BOOLEAN NOT NULL,
                recognize_photo BOOLEAN NOT NULL,
                load_from_date TIMESTAMP,
                system_prompt VARCHAR,
                answer_threshold FLOAT
            )
        """))
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client for testing."""

    class MockTelegramClient:
        def __init__(self):
            self.messages = []
            self.chats = []
            self.users = []

        async def iter_messages(self, entity, **kwargs):
            for msg in self.messages:
                yield msg

        async def iter_dialogs(self):
            for dialog in self.chats:
                yield dialog

        async def send_read_acknowledge(self, chat, message):
            pass

    return MockTelegramClient()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""

    class MockOpenAIClient:
        def __init__(self):
            self.responses = []

        async def chat_completions_create(self, **kwargs):
            class MockMessage:
                def __init__(self, content):
                    self.content = content

            class MockChoice:
                def __init__(self, content):
                    self.message = MockMessage(content)

            class MockResponse:
                def __init__(self, content):
                    self.choices = [MockChoice(content)]

            return MockResponse('{"context": "test context", "meaning": "test meaning"}')

        async def embeddings_create(self, **kwargs):
            class MockEmbeddingData:
                def __init__(self):
                    self.embedding = [0.1] * 4096

            class MockEmbeddingResponse:
                def __init__(self):
                    self.data = [MockEmbeddingData()]

            return MockEmbeddingResponse()

    return MockOpenAIClient()


@pytest.fixture
def sample_chat_data():
    """Sample chat data for testing."""
    return {
        "id": 123456789,
        "chat_type": "Channel",
        "title": "Test Channel",
        "username": "testchannel",
        "is_verified": False,
        "is_scam": False,
        "is_fake": False,
        "member_count": 1000,
        "raw_data": {
            "id": 123456789,
            "title": "Test Channel",
            "username": "testchannel",
            "verified": False,
            "scam": False,
            "fake": False,
            "participants_count": 1000,
        },
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": 987654321,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "is_bot": False,
        "is_verified": False,
        "is_scam": False,
        "is_fake": False,
        "is_premium": False,
        "raw_data": {
            "id": 987654321,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "bot": False,
            "verified": False,
            "scam": False,
            "fake": False,
            "premium": False,
        },
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "message_id": 111,
        "chat_id": 123456789,
        "sender_id": 987654321,
        "date": "2024-01-01T12:00:00Z",
        "message_type": "text",
        "is_read": False,
        "is_deleted": False,
        "raw_data": {
            "id": 111,
            "chat_id": 123456789,
            "sender_id": 987654321,
            "date": "2024-01-01T12:00:00Z",
            "message": "Test message",
            "media": None,
        },
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    os.environ["TELEGRAM_API_ID"] = "test_api_id"
    os.environ["TELEGRAM_API_HASH"] = "test_api_hash"
    os.environ["NEBIUS_STUDIO_API_KEY"] = "test_nebius_key"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    yield

    # Clean up environment variables
    for key in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "NEBIUS_STUDIO_API_KEY", "DATABASE_URL"]:
        if key in os.environ:
            del os.environ[key]
