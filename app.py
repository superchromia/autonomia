import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from api import v1_router
from dependency import dependency
from jobs.fetch_messages import fetch_all_messages_job
from models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    loop = asyncio.get_event_loop()

    # Apply Alembic migrations
    try:
        logger.info("Applying Alembic migrations...")
        from alembic import command
        from alembic.config import Config

        # Create configuration programmatically
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("prepend_sys_path", ".")
        alembic_cfg.set_main_option("path_separator", "os")

        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply Alembic migrations: {e}")
        # Create tables as fallback
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
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("app")


# Include API routers
app.include_router(v1_router)


async def start_telethon():
    """Start and run the Telegram client until disconnected."""
    await dependency.telegram_client.start()
    await dependency.telegram_client.run_until_disconnected()
