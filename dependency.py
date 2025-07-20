import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from telethon import TelegramClient
from telethon.sessions import StringSession

# Get environment variables with fallback values
DATABASE_URL = os.environ.get("DATABASE_URL")
API_ID = os.environ.get("TELEGRAM_API_ID")
API_HASH = os.environ.get("TELEGRAM_API_HASH")
SESSION = os.environ.get("TELETHON_SESSION", "anon")
SESSION_STRING = os.environ.get("TELETHON_SESSION_STRING")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER")

logger = logging.getLogger("dependency")
logger.info(f"DATABASE_URL: {DATABASE_URL}")

# Convert DATABASE_URL for Render (if needed)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql+asyncpg://", 1
    )

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Dependency:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.engine = engine
        self.async_session = async_session
        self.telegram_client = TelegramClient(
            StringSession(SESSION_STRING), int(API_ID), API_HASH
        )

    async def get_session(self):
        async with self.async_session() as session:
            yield session


dependency = Dependency()
