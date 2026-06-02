from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .config import settings
from .database import init_db
from .routes.api import router as api_router
from .routes.ui import router as ui_router

app = FastAPI(title=settings.APP_NAME)

base_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))
app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

app.include_router(api_router)
app.include_router(ui_router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
