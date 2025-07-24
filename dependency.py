import asyncio
import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from telethon import TelegramClient
from telethon.sessions import StringSession

from config import config

logger = logging.getLogger("dependency")

# Fix DATABASE_URL to use correct async driver if needed
database_url = config.database_url
parsed = urlparse(database_url)
if parsed.scheme != "postgresql+asyncpg":
    # Reconstruct URL with correct scheme
    database_url = urlunparse(("postgresql+asyncpg",) + parsed[1:])


engine = create_async_engine(database_url, future=True)
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

        # Validate required Telegram config
        config.validate_required_telegram_config()

        self.telegram_client = TelegramClient(
            session=StringSession(config.telethon_session_string),
            api_id=int(config.telegram_api_id),
            api_hash=config.telegram_api_hash,
            sequential_updates=True,
        )

    async def get_session(self):
        async with self.async_session() as session:
            yield session

    async def __start_telethon(self):
        """Start and run the Telegram client until disconnected."""
        await self.telegram_client.start()
        await self.telegram_client.run_until_disconnected()

    async def init_telegram_client(self):
        """Make sure telegram client connected and authorized"""
        loop = asyncio.get_event_loop()
        loop.create_task(self.__start_telethon())
        logger.info("Telegram client started")

        while not (
            self.telegram_client.is_connected()
            and await self.telegram_client.is_user_authorized()
        ):
            logger.info("Waiting for Telegram client to be authorized...")
            await asyncio.sleep(1)
        me = await self.telegram_client.get_me()
        logger.info(f"Telegram client started for @{me.username}")
        await self.telegram_client.catch_up()
        logger.info("Telegram client caught up")


dependency = Dependency()
