import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Telethon hook is automatically registered when imported
import jobs.telethon_hook  # noqa: F401
from admin import setup_admin
from api import v1_router
from config import config
from dependency import dependency
from jobs.fetch_messages import fetch_all_messages_job
from jobs.sync_dialogs import sync_dialogs_job


@asynccontextmanager
async def lifespan(app: FastAPI):
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

    scheduler.add_job(fetch_all_messages_job, CronTrigger(hour=1))
    scheduler.add_job(sync_dialogs_job, CronTrigger(hour=2))

    scheduler.start()
    await dependency.init_telegram_client()
    asyncio.create_task(sync_dialogs_job())
    yield

    # Shutdown
    scheduler.shutdown()
    if dependency.telegram_client:
        await dependency.telegram_client.disconnect()


app = FastAPI(title="Superchromia API", version="1.0.0", lifespan=lifespan)
scheduler = AsyncIOScheduler()

# Add session middleware for admin authentication
app.add_middleware(SessionMiddleware, secret_key=config.secret_key)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Superchromia API is running", "version": "1.0.0"}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("app")

# Setup SQLAdmin
admin = setup_admin(app, dependency.engine)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routers
app.include_router(v1_router)
