import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi import Query
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from telethon import TelegramClient

from dependency import async_session, dependency, engine
from jobs import telethon_hook
from jobs.fetch_messages import fetch_all_messages_job
from models.base import Base
from repositories.event_repository import EventRepository
from repositories.message_repository import MessageRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    loop = asyncio.get_event_loop()

    # Применение миграций Alembic
    try:
        logger.info("Applying Alembic migrations...")
        from alembic.config import Config
        from alembic import command
        
        # Создаем конфигурацию программно
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("prepend_sys_path", ".")
        alembic_cfg.set_main_option("path_separator", "os")
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply Alembic migrations: {e}")
        # Создание таблиц как fallback
        async with dependency.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    scheduler.add_job(fetch_all_messages_job, IntervalTrigger(minutes=60))
    scheduler.start()

    if dependency.telegram_client:
        loop.create_task(start_telethon())
    else:
        logger.warning("Telegram client not initialized - API credentials not provided")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    if dependency.telegram_client:
        await dependency.telegram_client.disconnect()




app = FastAPI(title="Superchromia API", version="1.0.0", lifespan=lifespan)
scheduler = AsyncIOScheduler()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("app")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

async def start_telethon():
    await dependency.telegram_client.start()
    await dependency.telegram_client.run_until_disconnected()

