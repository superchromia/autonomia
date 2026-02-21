import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Setup logging first
from logging_config import setup_logging

# pylint: disable=unused-import


setup_logging()

# Telethon hook is automatically registered when imported
import jobs.telethon_hook  # noqa: F401, E402
from admin import setup_admin  # noqa: E402
from api import v1_router  # noqa: E402
from config import config  # noqa: E402
from dependency import dependency  # noqa: E402
from jobs.fetch_messages import fetch_all_messages_job  # noqa: E402
from jobs.sync_dialogs import sync_dialogs_job  # noqa: E402
from scheduler_runtime import (  # noqa: E402
    scheduler,
    sync_scheduled_tasks,
    sync_scheduled_tasks_job,
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "MCP configuration loaded: enabled=%s (DB-only)",
        config.mcp_enabled,
    )

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

    scheduler.add_job(
        fetch_all_messages_job,
        CronTrigger.from_crontab("1/10 * * * *"),
        id="system_fetch_all_messages",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_dialogs_job,
        CronTrigger.from_crontab("3/10 * * * *"),
        id="system_sync_dialogs",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_scheduled_tasks_job,
        CronTrigger.from_crontab("* * * * *"),
        id="system_sync_scheduled_tasks",
        replace_existing=True,
    )
    scheduler.start()
    await sync_scheduled_tasks()
    await dependency.init_telegram_client()

    yield

    # Shutdown
    scheduler.shutdown()
    if dependency.telegram_client:
        await dependency.telegram_client.disconnect()


app = FastAPI(title="Superchromia API", version="1.0.0", lifespan=lifespan)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to handle HTTPS redirects and forwarded headers."""

    async def dispatch(self, request: Request, call_next):
        # Check if we're behind a proxy and get the real scheme
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")

        # If we're behind a proxy and it's HTTP, redirect to HTTPS
        if forwarded_proto == "http" and forwarded_host:
            # Construct HTTPS URL
            https_url = f"https://{forwarded_host}{request.url.path}"
            if request.url.query:
                https_url += f"?{request.url.query}"
            return Response(
                status_code=301,
                headers={"Location": https_url},
                content="Redirecting to HTTPS",
            )

        # Set the scheme to HTTPS if we're behind a proxy
        if forwarded_proto == "https":
            request.scope["scheme"] = "https"

        response = await call_next(request)
        return response


# Add HTTPS redirect middleware
app.add_middleware(HTTPSRedirectMiddleware)

# Add session middleware for admin authentication
app.add_middleware(SessionMiddleware, secret_key=config.secret_key)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Superchromia API is running", "version": "1.0.0"}


# Setup SQLAdmin
admin = setup_admin(app, dependency.engine)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include API routers
app.include_router(v1_router)
