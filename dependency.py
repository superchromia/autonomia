import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from telethon import TelegramClient

# Получение переменных окружения с fallback значениями
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/telegram')
API_ID = os.environ.get('TELEGRAM_API_ID')
API_HASH = os.environ.get('TELEGRAM_API_HASH')
SESSION = os.environ.get('TELETHON_SESSION', 'anon')

# Преобразование DATABASE_URL для Render (если нужно)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Dependency:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.engine = engine
        self.async_session = async_session
        # Инициализируем Telegram клиент только если есть API ключи
        if API_ID and API_HASH:
            self.telegram_client = TelegramClient(SESSION, int(API_ID), API_HASH)
        else:
            self.telegram_client = None

    async def get_session(self):
        async with self.async_session() as session:
            yield session

dependency = Dependency() 