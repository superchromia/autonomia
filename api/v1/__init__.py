from fastapi import APIRouter

from .health import router as health_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
