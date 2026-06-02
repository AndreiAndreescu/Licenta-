from fastapi import APIRouter

from .api import router as api_router
from .ui import router as ui_router

router = APIRouter()
router.include_router(api_router)
router.include_router(ui_router)
